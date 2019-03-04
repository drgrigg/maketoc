import re
import os
from bs4 import Tag, BeautifulSoup


class TocItem:
	filelink = ''
	level = 0
	roman = ''
	title = ''
	subtitle = ''
	id = ''

	def output(self):
		outstring = ''

		# now there are LOTS of combinations to deal with!
		if self.subtitle == '':  # no subtitle
			if self.roman != '':
				outstring += '\t<a href="../text/' + self.filelink + '">' + '<span epub:type="z3998:roman">' + self.roman + '</span></a>\n'
			else:
				outstring += '\t<a href="../text/' + self.filelink + '">' + self.title + '</a>\n'
		else:  # there is a subtitle
			if self.roman != '':
				outstring += '\t<a href="../text/' + self.filelink + '">' + '<span epub:type="z3998:roman">' + self.roman + '</span>: ' + self.subtitle + '</a>\n'
			else:
				outstring += '\t<a href="../text/' + self.filelink + '">' + self.title + ': ' + self.subtitle + '</a>\n'

		return outstring


def getcontentfiles(filename):
	temptext = gethtml(filename)
	opf = BeautifulSoup(temptext, 'html.parser')
	itemrefs = opf.find_all('itemref')
	retlist = []
	for itemref in itemrefs:
		retlist.append(itemref['idref'])
	return retlist


def gethtml(filename):
	try:
		fileobject = open(filename, 'r')
	except IOError:
		print('Could not open ' + filename)
		return ''
	text = fileobject.read()
	fileobject.close()
	return text


def outputtoc(listofitems, outpath):
	if len(listofitems) < 2:
		return

	try:
		os.remove(outpath + 'tempToC.txt')  # get rid of file if it already exists
		outfile = open(outpath + 'tempToC.txt', 'a')
	except IOError:
		print('Unable to open output file!')
		return

	# output ToC header
	tocstart = ''
	tocstart += '<?xml version="1.0" encoding="utf-8"?>\n'
	tocstart += '<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" epub:prefix="z3998: http://www.daisy.org/z3998/2012/vocab/structure/, se: https://standardebooks.org/vocab/1.0" xml:lang="en-US">\n'
	tocstart += '\t<head>\n'
	tocstart += '\t\t<title>Table of Contents</title>\n'
	tocstart += '\t</head>\n'
	tocstart += '\t<body epub:type="frontmatter">\n'
	tocstart += '\t\t<nav epub:type="toc">\n'
	tocstart += '\t\t\t<h2 epub:type="title">Table of Contents</h2>\n'
	tocstart += '\t\t\t<ol>\n'
	print(tocstart, end='')
	outfile.write(tocstart)

	# process all but last item so we can look ahead
	for index in range(0, len(listofitems) - 2):
		thisitem = listofitems[index]
		nextitem = listofitems[index + 1]

		lefttabs = '\t' * thisitem.level

		toprint = ''
		# check to see if next item is at same, lower or higher level than us
		if nextitem.level == thisitem.level:  # SIMPLE
			toprint += lefttabs + '<li>\n'
			toprint += lefttabs + thisitem.output()
			toprint += lefttabs + '</li>\n'
		if nextitem.level > thisitem.level:  # PARENT
			toprint += lefttabs + '<li>\n'
			toprint += lefttabs + thisitem.output()
			toprint += lefttabs + '\t<ol>\n'
		if nextitem.level < thisitem.level:  # LAST CHILD
			toprint += lefttabs + '<li>\n'
			toprint += lefttabs + thisitem.output()
			toprint += lefttabs + '</li>\n'  # end of this item
			toprint += lefttabs + '</ol>\n'  # end of embedded list
			toprint += lefttabs + '</li>\n'  # end of parent item

		print(toprint, end='')
		outfile.write(toprint)

	lastitem = listofitems[len(listofitems) - 1]

	lefttabs = '\t' * lastitem.level
	toprint = ''
	toprint += lefttabs + '<li>\n'
	toprint += lefttabs + lastitem.output()
	toprint += lefttabs + '</li>\n'
	toprint += lefttabs + '</ol>\n'

	print(toprint, end='')
	outfile.write(toprint)
	# eventually, write landmarks to file, too.
	tocend = ''
	tocend += '\t\t</nav>\n'
	tocend += '\t</body\n'
	tocend += '</html>\n'
	print(tocend, end='')
	outfile.write(tocend)

	outfile.close()


def getmyid(hchild):
	myid = ''
	dad = hchild.parent

	while myid == '':
		try:
			myid = dad['id']
		except KeyError:
			myid = ''
			dad = dad.parent

	return myid


rootpath = '/Users/david/Dropbox/Standard Ebooks/Bulfinch/thomas-bulfinch_bulfinchs-mythology/'
epubpath = rootpath + 'src/epub/'
textpath = epubpath + 'text/'
filelist = getcontentfiles(epubpath + 'content.opf')
toclist = []

for textf in filelist:
	html_text = gethtml(textpath + textf)
	soup = BeautifulSoup(html_text, 'html.parser')
	print('Processing: ' + textf)

	# find all the h1, h2 etc headers
	heads = soup.find_all(re.compile('h\d'))
	istoplevel = True

	for h in heads:
		tocitem = TocItem()
		tocitem.level = int(h.name[-1])
		# this stops the first header in a file getting an anchor id, which is what we want
		if istoplevel:
			tocitem.id = ''
			tocitem.filelink = textf
			istoplevel = False
		else:
			tocitem.id = getmyid(h)
			if tocitem.id == '':
				tocitem.filelink = textf
			else:
				tocitem.filelink = textf + '#' + tocitem.id

		for child in h.children:
			if child != '\n':
				if isinstance(child, Tag):
					try:
						spantype = child['epub:type']
					except KeyError:
						spantype = 'blank'

					if spantype == 'z3998:roman':
						tocitem.roman = child.string
					else:
						if spantype == 'subtitle':
							tocitem.subtitle = child.string
						else:
							tocitem.title = child.string
				else:
					tocitem.title = child.string
		toclist.append(tocitem)

outputtoc(toclist, rootpath)
print('done!')






