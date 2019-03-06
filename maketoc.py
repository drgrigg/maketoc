#!/usr/bin/env python3
"""
routine which tries to create a valid table of contents file for SE projects
"""
import argparse
import os
from bs4 import BeautifulSoup, Tag


class TocItem:
	"""
	small class to hold data on each table of contents item found in the project
	"""
	filelink = ''
	level = 0
	roman = ''
	title = ''
	subtitle = ''
	id = ''

	def output(self):
		"""
		the output method just outputs the linking tag line eg <a href=... depending on the data found
		"""
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
	"""
	reads the spine from content.opf to obtain a list of content files in the order wanted for the ToC
	"""
	temptext = gethtml(filename)
	opf = BeautifulSoup(temptext, 'html.parser')
	itemrefs = opf.find_all('itemref')
	retlist = []
	for itemref in itemrefs:
		retlist.append(itemref['idref'])
	return retlist


def gethtml(filename):
	"""
	reads an xhtml file and returns the text
	"""
	try:
		fileobject = open(filename, 'r', encoding='utf-8')
	except IOError:
		print('Could not open ' + filename)
		return ''
	text = fileobject.read()
	fileobject.close()
	return text


def readtocshell(tocpath):
	"""
	reads the existing toc and returns its start lines up until and including first <ol>
	and end lines from final </ol> before landmarks
	"""
	try:
		fileobject = open(tocpath, 'r', encoding='utf-8')
	except IOError:
		print('Could not open ' + tocpath)
		return ''
	alllines = fileobject.readlines()
	fileobject.close()
	startlines = []
	endlines = []
	for index in range(0, len(alllines)):
		line = alllines[index]
		if '<ol>' not in line:
			startlines.append(line)
		else:
			startlines.append(line)
			break
	alllines.reverse()
	for index in range(0, len(alllines)):
		line = alllines[index]
		if '<nav' not in line:
			endlines.append(line)
		else:
			endlines.append(line)
			endlines.append(alllines[index + 1])
			endlines.append(alllines[index + 2])
			endlines.reverse()
			break
	returnedlines = [startlines, endlines]
	return returnedlines


def process_items(item_list, tocfile):
	"""
	goes through all found toc items and writes them to the toc file
	"""
	unclosed_ol = 0   # keep track of how many ordered lists we open

	# process all but last item so we can look ahead
	for index in range(0, len(item_list) - 2):  # ignore very last item, which is a dummy
		thisitem = item_list[index]
		nextitem = item_list[index + 1]

		indent_none = '\t' * thisitem.level
		indent_one = '\t' * (thisitem.level + 1)
		indent_two = '\t' * (thisitem.level + 2)

		toprint = ''

		# check to see if next item is at same, lower or higher level than us
		if nextitem.level == thisitem.level:  # SIMPLE
			toprint += indent_two + '<li>\n'
			toprint += indent_two + thisitem.output()
			toprint += indent_two + '</li>\n'

		if nextitem.level > thisitem.level:  # PARENT
			toprint += indent_two + '<li>\n'
			toprint += indent_two + thisitem.output()
			toprint += indent_two + '\t<ol>\n'
			unclosed_ol += 1

		if nextitem.level < thisitem.level:  # LAST CHILD
			toprint += indent_two + '<li>\n'
			toprint += indent_two + thisitem.output()
			toprint += indent_two + '</li>\n'  # end of this item
			torepeat = thisitem.level - nextitem.level
			# handle special case of halftitle as NEXT item: don't want to close off <ol> when we hit it.
			# so treat as being same level as preceding item
			if torepeat < 0 or nextitem.filelink == 'halftitle.xhtml':
				torepeat = 0
			for _ in range(0, torepeat):  # need to repeat as may be jumping back from eg h5 to h2
				toprint += indent_one + '</ol>\n'  # end of embedded list
				unclosed_ol -= 1
				toprint += indent_none + '</li>\n'  # end of parent item

		tocfile.write(toprint)

	while unclosed_ol > 0:
		tocfile.write('\t\t\t</ol>\n')
		unclosed_ol -= 1
		tocfile.write('\t\t</li>\n')


def outputtoc(item_list, tocpath, outtocpath):
	"""
	outputs the contructed ToC based on the list of items found, to the specified output file
	"""
	if len(item_list) < 2:
		print('Too few ToC items found')
		return

	startends = readtocshell(tocpath)  # this returns a list of lists (start and end)

	try:
		if os.path.exists(outtocpath):
			os.remove(outtocpath)  # get rid of file if it already exists
		tocfile = open(outtocpath, 'a', encoding='utf-8')
	except IOError:
		print('Unable to open output file!')
		return

	# output ToC header
	for line in startends[0]:  # start of existing ToC
		tocfile.write(line)

	process_items(item_list, tocfile)

	for line in startends[1]:  # this is the ending part of the ToC file
		tocfile.write(line)

	tocfile.close()


def getmyid(hchild):
	"""
	climbs up the document tree looking for parent id (usually in a <section> tag.
	"""
	myid = ''
	dad = hchild.parent

	while myid == '':
		try:
			myid = dad['id']
		except KeyError:
			myid = ''
			dad = dad.parent  # query: what error do we get if there is no parent?

	return myid


def extractstrings(child):
	"""
	returns the string content only of a tag (ignores embedded <abbr> etc)
	"""
	retstring = ''
	for string in child.strings:
		retstring += string
	return retstring


def process_headers(soup, textf, toclist):
	"""
	find headers and extract data into items added to toclist
	"""
	# find all the h1, h2 etc headers
	heads = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
	is_toplevel = True
	for header in heads:
		tocitem = TocItem()
		tocitem.level = int(header.name[-1])
		# this stops the first header in a file getting an anchor id, which is what we want
		if is_toplevel:
			tocitem.id = ''
			tocitem.filelink = textf
			is_toplevel = False
		else:
			tocitem.id = getmyid(header)
			if tocitem.id == '':
				tocitem.filelink = textf
			else:
				tocitem.filelink = textf + '#' + tocitem.id

		# a header may include epub:type directly, eg <h5 epub:type="title z3998:roman">II</h5>
		try:
			attribs = header['epub:type']
			if 'z3998:roman' in attribs:
				tocitem.roman = extractstrings(header)
		except KeyError:
			print('header with no epub:type')

		for child in header.children:
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


def main():
	"""
	main routine of the tool
	"""
	parser = argparse.ArgumentParser(description="Attempts to build a table of contents for an SE project")
	parser.add_argument("-i", "--input", dest="input", required=True, help="root path of SE project")
	parser.add_argument("-o", "--output", dest="output", required=False, help="path and filename of output file")
	# parser.add_argument("targets", metavar="TARGET", nargs="+", help="an XHTML file, or a directory containing XHTML files")
	args = parser.parse_args()

	rootpath = args.input
	tocpath = os.path.join(rootpath, 'src', 'epub', 'toc.xhtml')
	textpath = os.path.join(rootpath, 'src', 'epub', 'text')
	opfpath = os.path.join(rootpath, 'src', 'epub', 'content.opf')
	filelist = getcontentfiles(opfpath)
	toclist = []

	for textf in filelist:
		# have to handle a special case here
		if textf == 'titlepage.xhtml':  # this doesn't have any header tags
			titletoc = TocItem()
			titletoc.level = 2
			titletoc.filelink = textf
			titletoc.title = 'Titlepage'
			toclist.append(titletoc)

		html_text = gethtml(os.path.join(textpath, textf))
		soup = BeautifulSoup(html_text, 'html.parser')
		print('Processing: ' + textf)

		process_headers(soup, textf, toclist)

	# we add this dummy item because outputtoc always needs to look ahead to the next item
	lasttoc = TocItem()
	lasttoc.level = 0
	lasttoc.title = "dummy"
	toclist.append(lasttoc)

	outpath = tocpath
	if args.output != '':
		outpath = args.output
	outputtoc(toclist, tocpath, outpath)
	print('done!')


if __name__ == "__main__":
	main()
