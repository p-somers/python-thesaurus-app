import urllib, urllib2, httplib
import json
import re
import xml.etree.ElementTree as ET
import sys
from file_parser import fromFile
from random import randint
from api_key import key

class Prog():

  def getSentences(self,list):
    if len(list) == 1:
      return list[0]
    else:
      rest = self.getSentences(list[1:len(list)])
      results = []
      for word in list[0]:
        for segment in rest:
          if re.match("[.,!?;]",segment) == None:
            #Only insert a space if the next character isn't punctuation
            if word.lower() == "a" and re.match("[aeiouAEIOU]",segment):
              results += [word+"n "+segment]
            else:
              results += [word+" "+segment]
          else:
            results += [word+segment]
      return results

  def getWords(self,word,type,desiredType):
    type = type.lower()
    desiredType = desiredType.lower()
    url     = "http://words.bighugelabs.com/api"
    version = "2"
    format  = "xml" #json, xml, or php. Blank = plain text
    full = url+"/"+version+"/"+key+"/"+word+"/"+format
    req = urllib2.Request(full)
    synonyms = []
    if not desiredType == 'ant':
      synonyms += [word]
    try:
      response = urllib2.urlopen(req)
      if ( response.getcode() == 200 ):
        tree = ET.parse(response)
        root = tree.getroot()
        for child in root:
        # child.attrib['p'] is the type of word it is grammatically
        # (I can't think of the word for that right now). child.attrib['r']
        # will return 'syn', 'ant', 'rel', or 'sim'. The actual word is
        # stored in child.text.
          if child.attrib['p'] == type and child.attrib['r'] == desiredType:
            synonyms += [child.text]
    except urllib2.HTTPError, e:
        pass
    return synonyms

  def getVariations(self,sentence, syntax, mode):
    sentence = re.findall(r"[\w']+|[.,!?;]",sentence)#split the sentence by punct. and whitespace
    if not len(sentence) == len(syntax):
      print "Error: the given sentence and the format specification have different lengths"
      return
    toCheck = ["adjective","noun","adverb","verb"]
    allPossibleWords = []
    for index in range(0,len(sentence)):
      word = sentence[index]
      if syntax[index].lower() not in toCheck:#not the most efficient thing, but it reduces requests
        allPossibleWords += [[word]]
      else:
        other_words = []
        if word.lower() in self.wordsRetreived[mode]:
          other_words = self.wordsRetreived[mode][word.lower()]#Again, reducing requests
        else:
          other_words = self.getWords(word,syntax[index],mode)
          self.wordsRetreived[mode][word.lower()] = other_words
        if len(other_words) == 0:
          allPossibleWords += [[word]]
        else:
          allPossibleWords += [other_words]
    return self.getSentences(allPossibleWords)

  def getPartsOfSpeech(self,sentence):
    params = urllib.urlencode({"text": str(sentence)})
    headers = { 
      "Connection": "keep-alive",
      "Content-Type": "application/xml"
    }
    name_entities = ['ORGANIZATION','PERSON','LOCATION','DATE','TIME','MONEY','PERCENT','FACILITY','GPE']
    conn = httplib.HTTPConnection("www.text-processing.com")
    conn.connect()
    conn.request("POST", "http://text-processing.com/api/tag/",params, headers)
    response = conn.getresponse()
    parts = []
    penn_treebank_tagset = {
      'CC':'coordinating conjunction',
      'CD':'cardinal number',
      'DT':'determiner',
      'EX':'existential there',
      'FW':'foreign word',
      'IN':'preposition/subordinating conjunction',
      'JJ':'adjective',
      'JJR':'adjective', #comparative
      'JJS':'adjective', #superlative
      'LS':'list item marker',
      'MD':'modal',
      'NN':'noun',# singular or mass  
      'NNS':'noun,',# plural  
      'NNP':'proper noun', #Proper, singular  
      'NNPS':'noun', #Proper, plural  
      'PDT':'predeterminer',
      'POS':'possessive ending',  
      'PRP':'pronoun', #personal
      'PRP$':'pronoun', #? Not sure why I need this, but it stops errors
      'PP$':'pronoun', #possessive
      'RB':'adverb',
      'RBR':'adverb', #comparative  
      'RBS':'adverb', #superlative  
      'RP':'particle',
      'SYM':'symbol', #(mathematical or scientific)  
      'TO':'to',
      'UH':'interjection',
      'VB':'verb', #base form
      'VBD':'verb', #past tense
      'VBG':'verb', #gerund/present participle 
      'VBN':'verb', #past participle
      'VBP':'verb', #non-3rd ps. sing. present 
      'VBZ':'verb', #3rd ps. sing. present
      'WDT':'wh', #determiner
      'WP':'wh', #pronoun
      'WP$':'wh', #Possessive pronoun
      'WRB':'wh', #adverb
      '.':'punctuation', #Sentence-final
      '$':'$','#':'#',',':',',':':':','(':'(',')':')','"':'"','\'':'\'','"':'"','\'':'\'','"':'"'
    }
    if ( response.status == 200 ):
      words = json.load(response)
      words = words['text'].split()
      for index in range(1,len(words)):
        word = words[index].strip("()")
        if not word in name_entities:
          forward_slash = word.find('/')
          if not forward_slash == -1:
            type = word[forward_slash+1:]#Finally getting the sentence type
            try:
              parts += [penn_treebank_tagset[type]]
            except BaseException:
              parts += ['Unknown'] 
    else:
      print "Error processing sentence:"
      print response.status, response.reason
    conn.close()
    return parts
  
  def setMode(self,new_mode):
    if new_mode == "syn" or new_mode == "synonym":
      self.mode = "syn"
    elif new_mode == "ant" or new_mode == "antonym":
      self.mode = "ant"
    elif new_mode == "rel" or new_mode == "related":
      self.mode = "rel"
    else:
      print "Unknown mode"
  
  def setSentence(self,sent):
    self.sentence = sent
    self.parts_of_speech = self.getPartsOfSpeech(self.sentence)
    self.results = self.getVariations(self.sentence, self.parts_of_speech, self.mode)
    self.longest = ""
    if len(self.results) == 1 and self.mode == "ant":
      print "No results."
    else:
      print "Number of results: " + str(len(self.results))
      for result in self.results:
        if len(result.split()) > len(self.longest.split()):
          self.longest = result
      print "Longest: "+self.longest
  
  def scanFromFile(self):
    app = wx.App(False)  # Create a new app, don't redirect stdout/stderr to a window.
    frame = wx.Frame(None, wx.ID_ANY, "Hello World") # A Frame is a top-level window.
    frame.Show(False)     # Show the frame.
    openFileDialog = wx.FileDialog(frame, "Open", "", "", "", wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
    openFileDialog.ShowModal()
    openFileDialog.Destroy()
    return str(fromFile(openFileDialog.GetPath())).strip()
  
  def __init__(self):
    self.wordsRetreived = {'syn':{},'ant':{},'rel':{}}
    self.loop = True
    self.help = ("Commands:\n"
                 "[e]nter: Input some text\n"
                 "[o]pen file: Scan in a text file\n"
                 "[l]ongest: Print out the longest result generated\n"
                 "[r]andom: Print a random one of the results\n"
                 "[p]rint: Prints all results\n"
                 "[s]how: Show tagged parts of speech\n"
                 "[c]hange: Manually change a part of speech assigned to a word\n"
                 "[m]ode: Can be [syn]onym, [ant]onym, or [rel]ated. Default is \"synonym\"\n"
                 "[h]elp: print this menu\n"
                 "[q]uit: Exits the program")
    self.sentence = ""
    self.results = []
    self.parts_of_speech = []
    self.longest = ""
    self.mode = "syn"
    print self.help
    while(self.loop):
      try:
        cmd = raw_input("Enter a command: ").lower().strip()
        if( cmd == "enter" or cmd == "e" ):
          self.setSentence(raw_input("Enter a sentence: "))
        elif( cmd == "open" or cmd == "o" ):
          self.setSentence(self.scanFromFile())
        elif( cmd == "longest" or cmd == "l" ):
          print self.longest
        elif( cmd == "random" or cmd == "r" ):
          if len(self.sentence) == 0:
            print "You haven't entered a sentence yet!"
          elif len(self.results) == 0:
            print "No results."
          else:
            print self.results[randint(0,len(self.results)-1)]
        elif( cmd == "print" or cmd == "p" ):
          for result in self.results:
            print result
        elif( cmd == "show" or cmd == "s" ):
          words = self.sentence.split()
          for index in range(0,len(words)):
            print str(index)+": "+words[index]+" = "+self.parts_of_speech[index]
        elif( cmd == "change" or cmd == "c" ):
          pass #todo
        elif( cmd == "mode" or cmd == "m" ):
          self.setMode(raw_input("Set mode: "))
        elif( cmd == "help" or cmd == "h" ):
          print self.help
        elif( cmd == "quit" or cmd == "q" ):
          self.loop = False
      except BaseException:
        print "Whoops, some error..."
p = Prog()