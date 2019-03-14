#!/usr/bin/env python3
"""
routine which tries to create a valid table of contents file for SE projects
"""
import argparse
import os
from typing import TextIO
from enum import Enum
import regex

from bs4 import BeautifulSoup, Tag


# global variables
worktitle = 'WORKTITLE'
worktype = 'fiction'


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
	epubtype = ''

	def output(self) -> str:
		"""
		the output method just outputs the linking tag line eg <a href=... depending on the data found
		"""
		outstring = ''

		if title_is_entirely_roman(self.title):
			if self.subtitle == '':  # no subtitle
				outstring += '\t<a href="text/' + self.filelink + '" epub:type="z3998:roman">' + self.roman + '</a>\n'
			else:
				outstring += '\t<a href="text/' + self.filelink + '">' + self.title + ': ' + self.subtitle + '</a>\n'
		else:
			outstring += '\t<a href="text/' + self.filelink + '">' + self.title + '</a>\n'

		return outstring


class Position(Enum):
	"""
	enum to indicate whether a landmark is frontmatter, bodymatter or backmatter
	"""
	FRONT = 1
	BODY = 2
	BACK = 3


class LandmarkItem:
	"""
	small class to hold data on landmark items found in the project
	"""
	title = ''
	filelink = ''
	epubtype = ''
	place: Position = Position.FRONT

	def output(self):
		indent = '\t' * 4
		indent_more = '\t' * 5
		if self.place == Position.FRONT:
			outstring = indent + '<li>\n' + indent_more + '<a href="text/' + self.filelink \
						+ '" epub:type="frontmatter ' + self.epubtype + '">' + self.title + '</a>\n' + indent + '</li>\n'
		if self.place == Position.BODY:
			outstring = indent + '<li>\n' + indent_more + '<a href="text/' + self.filelink \
						+ '" epub:type="bodymatter z3998:' + worktype + '">' + worktitle + '</a>\n' + indent + '</li>\n'
		if self.place == Position.BACK:
			outstring = indent + '<li>\n' + indent_more + '<a href="text/' + self.filelink \
						+ '" epub:type="backmatter ' + self.epubtype + '">' + self.title + '</a>\n' + indent + '</li>\n'

		return outstring


def getcontentfiles(filename: str) -> list:
	"""
	reads the spine from content.opf to obtain a list of content files in the order wanted for the ToC
	"""
	temptext = gethtml(filename)
	opf = BeautifulSoup(temptext, 'html.parser')
	dctitle = opf.find('dc:title')
	if dctitle is not None:
		global worktitle
		worktitle = dctitle.string
	itemrefs = opf.find_all('itemref')
	retlist = []
	for itemref in itemrefs:
		retlist.append(itemref['idref'])
	return retlist


def gethtml(filename: str) -> str:
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


def get_epub_type(soup: BeautifulSoup) -> str:
	"""
	retrieve the epubtype of this file to see if it's a landmark item
	"""
	# try for a heading
	first_head = soup.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
	if first_head is not None:
		parent = first_head.find_parent(['section', 'article'])
		try:
			return parent['epub:type']
		except KeyError:
			return ''
	else:
		first_section = soup.find(['section', 'article'])
		try:
			return first_section['epub:type']
		except KeyError:
			return ''


def add_landmark(soup: BeautifulSoup, textf: str, landmarks: list):
	epubtype = get_epub_type(soup)
	title = soup.find('title').string
	landmark = LandmarkItem()
	landmark.title = title
	if epubtype != '':
		landmark.epubtype = epubtype
		landmark.filelink = textf
		if epubtype in FRONTMATTER_TYPES:
			landmark.place = Position.FRONT
		elif epubtype in BACKMATTER_TYPES:
			landmark.place = Position.BACK
		else:
			landmark.place = Position.BODY  # we'll discard all but the first of these
		landmarks.append(landmark)


def read_toc_start(tocpath: str) -> list:
	"""
	reads the existing toc and returns its start lines up until and including first <ol>
	and end lines from final </ol> before landmarks
	"""
	try:
		fileobject = open(tocpath, 'r', encoding='utf-8')
	except IOError:
		print('Could not open ' + tocpath)
		return []
	alllines = fileobject.readlines()
	fileobject.close()
	startlines = []
	for index in range(0, len(alllines)):
		line = alllines[index]
		if '<ol>' not in line:
			startlines.append(line)
		else:
			startlines.append(line)
			break
	return startlines


def process_landmarks(landmarks_list: list, tocfile: TextIO):
	"""
	goes through all found landmark items and writes them to the toc file
	"""
	frontitems = [item for item in landmarks_list if item.place == Position.FRONT]
	bodyitems = [item for item in landmarks_list if item.place == Position.BODY]
	backitems = [item for item in landmarks_list if item.place == Position.BACK]

	for item in frontitems:
		tocfile.write(item.output())

	tocfile.write(bodyitems[0].output())  # just the first of these

	for item in backitems:
		tocfile.write(item.output())


def process_items(item_list: list, tocfile: TextIO):
	"""
	goes through all found toc items and writes them to the toc file
	"""
	unclosed_ol = 0   # keep track of how many ordered lists we open

	# process all but last item so we can look ahead
	for index in range(0, len(item_list) - 1):  # ignore very last item, which is a dummy
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
			# print(thisitem.filelink + ' unclosed ol = ' + str(unclosed_ol))

		if nextitem.level < thisitem.level:  # LAST CHILD
			toprint += indent_two + '<li>\n'
			toprint += indent_two + thisitem.output()
			toprint += indent_two + '</li>\n'  # end of this item
			torepeat = thisitem.level - nextitem.level

			if torepeat > 0:
				for _ in range(0, torepeat):  # need to repeat a few times as may be jumping back from eg h5 to h2
					toprint += indent_one + '</ol>\n'  # end of embedded list
					unclosed_ol -= 1
					# print(thisitem.filelink + ' unclosed ol = ' + str(unclosed_ol))
					toprint += indent_none + '</li>\n'  # end of parent item

		tocfile.write(toprint)

	while unclosed_ol > 0:
		tocfile.write('\t\t\t</ol>\n')
		unclosed_ol -= 1
		# print('Closing: unclosed ol = ' + str(unclosed_ol))
		tocfile.write('\t\t</li>\n')


def output_toc(item_list: list, landmark_list, tocpath: str, outtocpath: str):
	"""
	outputs the contructed ToC based on the list of items found, to the specified output file
	"""
	if len(item_list) < 2:
		print('Too few ToC items found')
		return

	starttoc = read_toc_start(tocpath)  # this returns the start of the existing ToC

	try:
		if os.path.exists(outtocpath):
			os.remove(outtocpath)  # get rid of file if it already exists
		tocfile = open(outtocpath, 'a', encoding='utf-8')
	except IOError:
		print('Unable to open output file! ' + outtocpath)
		return

	for line in starttoc:  # this is the starting part of existing ToC, includes first <ol>
		tocfile.write(line)

	process_items(item_list, tocfile)

	tocfile.write('\t\t\t</ol>\n')
	tocfile.write('\t\t</nav>\n')
	tocfile.write('\t\t<nav epub:type="landmarks">\n')
	tocfile.write('\t\t\t<h2 epub:type="title">Landmarks</h2>\n')
	tocfile.write('\t\t\t<ol>\n')

	process_landmarks(landmark_list, tocfile)

	tocfile.write('\t\t\t</ol>\n')
	tocfile.write('\t\t</nav>\n')
	tocfile.write('\t</body>\n')
	tocfile.write('</html>')

	tocfile.close()


def get_parent_id(hchild: Tag) -> str:
	"""
	climbs up the document tree looking for parent id in a <section> tag.
	"""
	parent = hchild.find_parent("section")
	if parent is None:
		return ''
	try:
		return parent['id']
	except KeyError:
		return ''


def extract_strings(atag: Tag) -> str:
	"""
	returns only the string content of a tag, ignoring noteref and its content
	"""
	retstring = ''
	for child in atag.contents:
		if child != '\n':
			if isinstance(child, Tag):
				try:
					epubtype = child['epub:type']
					if 'z3998:roman' in epubtype:
						retstring += str(child)  # want the whole span
					if 'noteref' in epubtype:
						continue
				except KeyError:  # tag has no epubtype, probably <abbr>
					retstring += child.string
			else:
				retstring += child  # must be NavigableString
	return retstring


def process_headings(soup: BeautifulSoup, textf: str, toclist: list, nest_under_halftitle: bool):
	"""
	find headings in current file and extract data into items added to toclist
	"""
	# find all the h1, h2 etc headings
	heads = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])

	if not heads:  # may be a dedication or an epigraph, etc with no heading tag
		special_item = TocItem()
		sections = soup.find_all('section')  # count the sections within this file
		special_item.level = len(sections)
		title_tag = soup.find('title')  # use page title as the ToC entry title
		special_item.title = title_tag.string
		special_item.filelink = textf
		toclist.append(special_item)
		return

	is_toplevel = True
	for heading in heads:
		tocitem = process_heading(heading, is_toplevel, textf)
		if nest_under_halftitle:
			tocitem.level += 1
		is_toplevel = False
		toclist.append(tocitem)


def title_is_entirely_roman(title: str) -> bool:
	"""
	test to see if there's nothing else in a title than a roman number.
	if so, we can collapse the epub type into the surrounding ToC <a> tag
	"""
	pattern = r'^<span epub:type="z3998:roman">[IVXLC]{1,10}<\/span>$'
	compiled_regex = regex.compile(pattern)
	return compiled_regex.search(title)


def process_heading(heading, is_toplevel, textf) -> TocItem:
	"""
	generate and return a TocItem from this heading
	"""
	tocitem = TocItem()
	parent_sections = heading.find_parents(['section', 'article'])
	tocitem.level = len(parent_sections)
	# this stops the first heading in a file getting an anchor id, which is what we want
	if is_toplevel:
		tocitem.id = ''
		tocitem.filelink = textf
	else:
		tocitem.id = get_parent_id(heading)
		if tocitem.id == '':
			tocitem.filelink = textf
		else:
			tocitem.filelink = textf + '#' + tocitem.id

	# a heading may include z3998:roman directly, eg <h5 epub:type="title z3998:roman">II</h5>
	try:
		attribs = heading['epub:type']
	except KeyError:
		print(textf + ': warning: heading with no epub:type')
		attribs = ''
	if 'z3998:roman' in attribs:
		tocitem.roman = extract_strings(heading)
		tocitem.title = '<span epub:type="z3998:roman">' + tocitem.roman + '</span>'
		return tocitem

	process_heading_contents(textf, heading, tocitem)

	return tocitem


def process_heading_contents(textf, heading, tocitem):
	"""
	go through each item in the heading contents and try to pull out the toc item data
	"""
	accumulator = ''  # we'll use this to build up the title
	for child in heading.contents:  # was children
		if child != '\n':
			if isinstance(child, Tag):
				try:
					epubtype = child['epub:type']
				except KeyError:
					epubtype = 'blank'
					if child.name == 'abbr':
						accumulator += extract_strings(child)
						continue  # skip the following and go on to next child

				if 'z3998:roman' in epubtype:
					tocitem.roman = extract_strings(child)
					accumulator += str(child)
				elif 'subtitle' in epubtype:
					tocitem.subtitle = extract_strings(child)
				elif 'title' in epubtype:
					tocitem.title = extract_strings(child)
				elif 'noteref' in epubtype:
					print(textf + ": ignoring noteref in heading")
				else:
					tocitem.title = extract_strings(child)
			else:  # should be a simple NavigableString
				accumulator += str(child)
	if tocitem.title == '':
		tocitem.title = accumulator


BACKMATTER_FILENAMES = ["endnotes.xhtml", "loi.xhtml", "afterword.xhtml", "appendix.xhtml", "colophon.xhtml", "uncopyright.xhtml", "glossary.xhtml"]
FRONTMATTER_TYPES = ['titlepage', 'imprint', 'dedication', 'epigraph', 'preface', 'introduction', 'preamble', 'foreword']
BACKMATTER_TYPES = ['afterword', 'loi', 'rearnotes', 'endnotes', 'conclusion', 'glossary', 'colophon', 'copyright-page']


def main():
	"""
	main routine of the tool
	"""
	parser = argparse.ArgumentParser(description="Attempts to build a table of contents for an SE project")
	parser.add_argument("-o", "--output", dest="output", required=False, help="path and filename of output file if existing ToC is to be left alone")
	parser.add_argument("-n", "--nonfiction", dest="nonfiction", required=False, help="set to Y if the work is non-fiction rather than fiction")
	parser.add_argument("directory", metavar="DIRECTORY", help="a Standard Ebooks source directory")
	args = parser.parse_args()

	rootpath = args.directory
	tocpath = os.path.join(rootpath, 'src', 'epub', 'toc.xhtml')
	textpath = os.path.join(rootpath, 'src', 'epub', 'text')
	opfpath = os.path.join(rootpath, 'src', 'epub', 'content.opf')
	filelist = getcontentfiles(opfpath)

	if not os.path.exists(opfpath):
		print("Error: this does not seem to be a Standard Ebooks root directory")
		exit(-1)

	global worktype
	if args.nonfiction == 'Y':
		worktype = 'non-fiction'
	else:
		worktype = 'fiction'

	toclist = []
	landmarks = []

	nest_under_halftitle = False

	for textf in filelist:
		# print('Processing: ' + textf)
		html_text = gethtml(os.path.join(textpath, textf))
		soup = BeautifulSoup(html_text, 'html.parser')
		if textf in BACKMATTER_FILENAMES:
			nest_under_halftitle = False
		process_headings(soup, textf, toclist, nest_under_halftitle)
		if textf == 'halftitle.xhtml':
			nest_under_halftitle = True
		add_landmark(soup, textf, landmarks)

	# we add this dummy item because outputtoc always needs to look ahead to the next item
	lasttoc = TocItem()
	lasttoc.level = 1
	lasttoc.title = "dummy"
	toclist.append(lasttoc)

	outpath = tocpath
	if args.output != '':
		outpath = args.output
	output_toc(toclist, landmarks, tocpath, outpath)
	print('done!')


if __name__ == "__main__":
	main()
