import cv2
import io
from string import Template
import requests
import re
from bs4 import BeautifulSoup
import json
from slimit import ast
from slimit.parser import Parser
from slimit.visitors import nodevisitor
from datetime import datetime
from itertools import izip
from Levenshtein import StringMatcher
from collections import namedtuple

CaptionElem = namedtuple('CaptionElem', ['timeStart', 'words'])
class MeetingCaption:

    def __init__(self, dateId, internalSrcId):
        self.captions = self._getSubtitles(dateId, internalSrcId)

    @staticmethod
    def _getDateIdAndInternalSourceId(source_id):
        linkToVideo = 'http://www.parl.gc.ca/Committees/en/Redirects/ParlVuMeetingPage?MeetingId=%(src_id)d'
        a = linkToVideo % {'src_id': source_id}
        response = requests.get(a)
        vidContent = response.text
        redirUrlMatch = re.compile('var url = \\\"http://parlvu.parl.gc.ca/XRender/en/PowerBrowser/PowerBrowserV2/([0-9-]+)/-1/([0-9]+)\\\";').search(vidContent)
        dateId = redirUrlMatch.group(1)
        internalSrcId = redirUrlMatch.group(2)
        return dateId, internalSrcId

    @classmethod
    def FromSourceId(cls, source_id):
        dateId, internalSrcId = MeetingCaption._getDateIdAndInternalSourceId(source_id)
        return MeetingCaption(dateId, internalSrcId)

    @classmethod
    def FromDateAndIntSourceId(cls, dateId, internalSrcId):
        return MeetingCaption(dateId, internalSrcId)


    def findTimeStart(self, orig_text, minTime, maxTime):
        needleWordList = orig_text.split()
        caption = self.captions

        #limit our search in the time range given.
        firstCaption = (i for i,v in enumerate(caption) if v.timeStart >= minTime)
        firstCaptionIndex = firstCaption.next()
        if firstCaptionIndex > 0:
            firstCaptionIndex = firstCaptionIndex-1
        lastCaption = (i for i,v in enumerate(caption[firstCaptionIndex:]) if v.timeStart >= maxTime)
        lastCaptionIndex = firstCaptionIndex+lastCaption.next()
        subCaptionList = caption[firstCaptionIndex:lastCaptionIndex]
        # print(caption[0], caption[-1], firstCaptionIndex, len(caption), minTime)
        # print("subCaptionList", subCaptionList)

        #find word list in the caption sub list
        haystackWordList = sum((c.words for c in subCaptionList), [])
        indexFound = self._findInText(needleWordList, haystackWordList)

        # print("found at ", haystackWordList[indexFound:indexFound+12])

        #get index in the caption for the found word index.
        partSumWord = reduce(lambda c, x: c + [c[-1] + len(x.words)], subCaptionList, [0])
        timeSumWordPairList = izip(partSumWord , (c.timeStart for c in subCaptionList))
        timeForIndex = (ind for ind,curWord in enumerate(partSumWord) if curWord >= indexFound).next()
        # print(timeForIndex, subCaptionList[timeForIndex])
        if timeForIndex > 0:
            timeForIndex = timeForIndex-1

        return subCaptionList[timeForIndex].timeStart

    def _readDateTime(self, s):
        try:
            timestamp = datetime.strptime(s, '%Y-%m-%dT%H:%M:%S.%f')
        except ValueError:
            timestamp = datetime.strptime(s, '%Y-%m-%dT%H:%M:%S')
        return timestamp

    _secondLinkPart1 = 'http://parlvu.parl.gc.ca/XRender/en/PowerBrowser/PowerBrowserV2/'
    _secondLinkPart2 = "?useragent=Mozilla/5.0%20(Macintosh;%20Intel%20Mac%20OS%20X%2010_12_4)%20AppleWebKit/537.36%20(KHTML,%20like%20Gecko)%20Chrome/57.0.2987.133%20Safari/537.36"
    def _getSubtitles(self, dateId, internalSrcId):
        print(datetime.now(), "_getSubtitles start")
        urlToVideoWebPage = self._secondLinkPart1 + dateId + '/-1/' + internalSrcId + self._secondLinkPart2
        response = requests.get(urlToVideoWebPage)
        text2 = response.text
        print(datetime.now(), "_getSubtitles after load html")
        soup = BeautifulSoup(response.text, 'html.parser')
        print(datetime.now(), "_getSubtitles after soup load")
        scripts = soup.findAll('script')
        ccScripts = filter(lambda s: s.string.find("ccItems") >= 0 if s.string else False, scripts)
        print(datetime.now(), "_getSubtitles after soup proc")
        if len(ccScripts) != 1:
            print(len(ccScripts), "ccscripts")
            return None
        ccScript = ccScripts[0]
        parser = Parser()
        print(datetime.now(), "_getSubtitles before javascript parse", len(ccScript.text))
        tree = parser.parse(ccScript.text)
        print(datetime.now(), "_getSubtitles after javascript parse")
        ccNode = filter(lambda n: isinstance(n, ast.Assign) and getattr(n.left, 'value', '') == 'ccItems', nodevisitor.visit(tree))
        if len(ccNode) < 1:
            print(len(ccNode), "ccNode")
            return None
        print(datetime.now(), "_getSubtitles before javascript to ecma")
        ccItemFull = "{ \"ccItems\": " + ccNode[0].right.to_ecma() + "}"
        print(datetime.now(), "_getSubtitles before javascript to ecma", len(ccItemFull))

        print(datetime.now(), "_getSubtitles before json load")
        ccJson = json.loads(ccItemFull)
        print(datetime.now(), "_getSubtitles after json load")
        enCC = ccJson['ccItems']['en']
        caption = []
        for t in enCC:
            timeStart = self._readDateTime(t['Begin'])
            text = t['Content']
            words = text.split()
            caption.append(CaptionElem(timeStart, words))
        print(datetime.now(), "_getSubtitles end")
        return caption

    #return the word index
    def _findInText(self, needle, haystack):
        shorter = unicode(''.join(needle)).upper()
        longer  = unicode(''.join(haystack)).upper()

        slen = len(shorter)
        dlen = len(longer)

        m = StringMatcher.StringMatcher(None, shorter, longer)
        blocks = m.get_matching_blocks()
        blocks = [[s, s+2*slen] for s in range(0,len(longer), slen/4)]

        # each block represents a sequence of matching characters in a string
        # of the form (idx_1, idx_2, len)
        # the best partial match will block align with at least one of those blocks
        #   e.g. shorter = "abcd", longer = XXXbcdeEEE
        #   block = (1,3,3)
        #   best score === ratio("abcd", "Xbcd")
        bestScore = 0
        bestBlockIndex = -1
        bestOperation = []
        for i,block in enumerate(blocks):
            long_start = max(0,block[0])
            long_end = min(block[1], dlen-1)
            # print("block : ", i, long_start, long_end)
            long_substr = longer[long_start:long_end]

            # match on the whole block.
            m2 = StringMatcher.StringMatcher(None, shorter, long_substr)
            r = m2.ratio()
            if r > bestScore:
                bestScore = r
                bestBlockIndex = i
                bestOperation = m2.get_editops()

        if bestScore < 0.20:
            return -1

        #find where in the block the match occur.
        # we compute the average offset position

        bestBlock = blocks[bestBlockIndex]
        # print("bestblock", bestBlock)
        bestBlockLen = bestBlock[1]-bestBlock[0]
        sumPos = 0
        nbPos = 0
        lastMatchDstPos = 0
        lastMatchSrcPos = 0
        lastMatchOffset = 0
        offsetArray = [0]*(bestBlockLen+1)
        # print(bestOperation)
        for op,spos,dpos in bestOperation:
            # print(op,spos,dpos, sumPos, nbPos, lastMatchOffset)
            diffPos = spos-lastMatchSrcPos
            sumPos = sumPos + (lastMatchOffset * diffPos )
            nbPos = nbPos + diffPos
            offsetArray[lastMatchOffset] += diffPos
            if op == 'insert':
                lastMatchOffset = lastMatchOffset+1
            if op == 'delete':
                lastMatchOffset = lastMatchOffset-1
            lastMatchDstPos = dpos
            lastMatchSrcPos = spos
        averageOffset = sumPos/nbPos
        sumHist = sum(offsetArray)
        partSumHist = reduce(lambda c, x: c + [c[-1] + x], offsetArray, [0])
        sumHistMidIndex = (ind for ind,curSum in enumerate(partSumHist) if curSum >= slen/2).next()
        # print("sumHist", sumHist, slen, bestBlockLen, sumHistMidIndex, averageOffset)
        # for i,v in enumerate(offsetArray):
        #     print(i,v)
        # print("strings", shorter, longer)
        averageOffset = sumHistMidIndex

        longerFoundIndex = bestBlock[0]+averageOffset-1
        longerFoundIndex = max(0, longerFoundIndex)
        # print("found at ", longer[longerFoundIndex:longerFoundIndex+25])
        partSumChar = reduce(lambda c, x: c + [c[-1] + len(x)], haystack, [0])
        wordIndex = (ind for ind,curChars in enumerate(partSumChar) if curChars >= longerFoundIndex).next()

        # print("found at ", haystack[wordIndex:wordIndex+12])
        # print('result',bestScore, bestBlockIndex, averageOffset, wordIndex)
        return wordIndex


def detectGen(textDateArray, meetingCaption):
    for t in textDateArray:
        tt = meetingCaption.findTimeStart(t[0], t[1], t[2])
        print("\t\t\t Found Time:  ", tt)

def detectFEWO():
    otext = "This is a fabulous day. Not only do we have the Minister of Status of Women here, but we also have a number of young ladies from the University of Toronto. I can't think of a better day for you all to be here, but our committee is always an interesting committee. I hope this inspires you. I'm fortunate to have two young ladies with me for the day. Welcome, and I hope you enjoy, are inspired, and consider politics as a venue as you go forward in your careers."
    otext2 = "Thank you very much, Madam Chair. Colleagues, friends, guests, allies, it's a great privilege to be in this room with you, the same room in which I was sworn in.  To be on this traditional territory of the Algonquin peoples is a reminder of the privileges we bring to this room but also the responsibility that comes with all that privilege."
    otext3 = "We can make sure that Canadian women and girls, and those of different intersecting identities feel more like they belong, and feel more like they can fully participate. Canada, as a result, I know will be strengthened. Thank you, Madam Chair. I am happy to answer any questions colleagues may have."
    otext4 = "My commitment to women and girls and gender equality, Rachael, is apparent. One of the reasons I'm here today is that I know there are challenges across all cultures when it comes to gender equality. As I look at my mother, I'm reminded of what can happen when women are given opportunities to succeed."
    otext5 = "Thank you, Pam. We know that 60% of those living with disabilities are vulnerable to gender-based violence. We know from our own personal and professional experiences that people with disabilities and exceptionalities bring gifts and talents to organizations and communities, gifts and talents that aren't always utilized, and as a result, we're not as strong as a nation as we could be."
    otexts = [
        [otext, datetime(2017, 3, 23, 8, 50), datetime(2017, 3, 23, 9, 10)],
        [otext2, datetime(2017, 3, 23, 8, 50), datetime(2017, 3, 23, 9, 10)],
        [otext3, datetime(2017, 3, 23, 9, 05), datetime(2017, 3, 23, 9, 20)],
        [otext4, datetime(2017, 3, 23, 9, 40), datetime(2017, 3, 23, 9, 50)],
        [otext5, datetime(2017, 3, 23, 9, 59), datetime(2017, 3, 23, 10, 10)],
        ] #[otext, otext2, otext3]
    detectGen(otexts, MeetingCaption.FromSourceId(9402591))

def detectDebates():
    otext = "It is important to note that 75% of properties in proximity to the rail line are inaccessible except by rail service. There has been a huge economic impact in the area, especially for the tourist outfitters. This also impacts first nations' access to remote regions of their traditional territories. The cancellation infringes on the federal government's obligation to have consultation with first nations."
    otext2 = "Mr. Speaker, the Prime Minister claims he is frustrated with Bombardier for using tax dollars to boost the paycheques of its executives. Frustrated? This is his deal. This is actually the Prime Minister's deal, so if he is frustrated with anyone, he should look in the mirror, because he is the one who did the deal with no strings attached. He gave Bombardier hundreds of millions of dollars while it was laying off thousands of people."
    otexts = [
        [otext, datetime(2017, 4, 4, 10, 5), datetime(2017, 4, 4, 10, 10)],
        [otext2, datetime(2017, 4, 4, 14, 15), datetime(2017, 4, 4, 14, 20)],
        ]
    detectGen(otexts, MeetingCaption.FromDateAndIntSourceId("20170404", str(27023)))

detectDebates()
print(datetime.now(), "After All")
# detectFEWO()
