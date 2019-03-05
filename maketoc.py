import argparse
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

		# there are LOTS of combinations to deal with!
		if self.subtitle == '':  # no subtitle
			if self.roman != '':
				outstring += '\t<a href="../text/' + self.filelink + '" epub:type="z3998:roman">' + self.roman + '</a>\n'
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
		fileobject = open(filename, 'r', encoding='utf-8')
	except IOError:
		print('Could not open ' + filename)
		return ''
	text = fileobject.read()
	fileobject.close()
	return text


def outputtoc(listofitems, outfile):
	if len(listofitems) < 2:
		return

	try:
		if os.path.exists(outfile):
			os.remove(outfile)  # get rid of file if it already exists
		outfile = open(outfile, 'a', encoding='utf-8')
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
	for index in range(0, len(listofitems) - 2):  # ignore very last item, which is a dummy
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
			leveldiff = thisitem.level - nextitem.level
			for x in range(0, leveldiff):  # repeat as may be jumping back from eg h5 to h2
				toprint += lefttabs + '</ol>\n'  # end of embedded list
				toprint += lefttabs + '</li>\n'  # end of parent item

		print(toprint, end='')
		outfile.write(toprint)

	# eventually, we will write landmarks to file, too.
	tocend = ''
	tocend += '\t\t</ol>\n'
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


def extractstrings(child):
	retstring = ''
	for s in child.strings:
		retstring += s
	return retstring


def main():
	parser = argparse.ArgumentParser(description="Attempts to build a table of contents for an SE project")
	parser.add_argument("-i", "--input", dest="input", required=True, help="root path of SE project")
	parser.add_argument("-o", "--output", dest="output", required=True, help="name of output file")
	args = parser.parse_args()

	# rootpath = '/Users/david/Dropbox/Standard Ebooks/Bulfinch/thomas-bulfinch_bulfinchs-mythology/'
	rootpath = args.input
	# srcpath = os.path.join(rootpath, 'src')
	# epubpath = os.path.join(srcpath, 'epub')
	textpath = os.path.join(rootpath, 'src', 'epub', 'text')
	opfpath = os.path.join(rootpath, 'src', 'epub', 'content.opf')
	filelist = getcontentfiles(opfpath)
	toclist = []

	for textf in filelist:
		html_text = gethtml(os.path.join(textpath, textf))
		soup = BeautifulSoup(html_text, 'html.parser')
		print('Processing: ' + textf)

		# find all the h1, h2 etc headers
		heads = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
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

			# a header may include epub:type directly, eg <h5 epub:type="title z3998:roman">II</h5>
			try:
				attribs = h['epub:type']
				if 'z3998:roman' in attribs:
					tocitem.roman = extractstrings(h)
			except KeyError:
				print('header with no epub:type')

			for child in h.children:
				if child != '\n':
					if isinstance(child, Tag):
						try:
							spantype = child['epub:type']
						except KeyError:
							spantype = 'blank'

						if spantype == 'z3998:roman':
							tocitem.roman = extractstrings(child)
						else:
							if spantype == 'subtitle':
								tocitem.subtitle = extractstrings(child)
							else:
								tocitem.title = extractstrings(child)
					else:  # it's a simple NavigableString
						tocitem.title = child.string
			toclist.append(tocitem)

	# we add this dummy item because outputtoc always needs to look ahead to the next item
	lasttoc = TocItem()
	lasttoc.level = 1
	lasttoc.title = "dummy"
	toclist.append(lasttoc)

	outfile = os.path.join(rootpath, args.output)
	outputtoc(toclist, outfile)
	print('done!')


if __name__ == "__main__":
	main()




