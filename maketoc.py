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
verbose = False


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
				outstring += tabs(1) + '<a href="text/' + self.filelink + '" epub:type="z3998:roman">' + self.roman + '</a>\n'
			else:
				outstring += tabs(1) + '<a href="text/' + self.filelink + '">' + self.title + ': ' + self.subtitle + '</a>\n'
		else:
			outstring += tabs(1) + '<a href="text/' + self.filelink + '">' + self.title + '</a>\n'

		return outstring


class Position(Enum):
	"""
	enum to indicate whether a landmark is frontmatter, bodymatter or backmatter
	"""
	NONE = 0
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
		if self.place == Position.FRONT:
			outstring = tabs(4) + '<li>\n' + tabs(5) + '<a href="text/' + self.filelink \
						+ '" epub:type="frontmatter ' + self.epubtype + '">' + self.title + '</a>\n' + tabs(4) + '</li>\n'
		if self.place == Position.BODY:
			outstring = tabs(4) + '<li>\n' + tabs(5) + '<a href="text/' + self.filelink \
						+ '" epub:type="bodymatter z3998:' + worktype + '">' + worktitle + '</a>\n' + tabs(4) + '</li>\n'
		if self.place == Position.BACK:
			outstring = tabs(4) + '<li>\n' + tabs(5) + '<a href="text/' + self.filelink \
						+ '" epub:type="backmatter ' + self.epubtype + '">' + self.title + '</a>\n' + tabs(4) + '</li>\n'
		return outstring


def tabs(num_tabs: int) -> str:
	"""
	convenience function to return given number of tabs as a string.
	offset is optional
	"""
	if num_tabs > 0:
		return '\t' * num_tabs
	else:
		return ''


def indent(level: int, offset: int = 0) -> str:
	"""
	convenience function to return given number of tabs as a string.
	offset is optional
	"""
	num_tabs = (level * 2 + 2) + offset  # offset may be negative
	if num_tabs > 0:
		return '\t' * num_tabs
	else:
		return ''


def getcontentfiles(filename: str) -> list:
	"""
	reads the spine from content.opf to obtain a list of content files in the order wanted for the ToC
	"""
	temptext = gethtml(filename)
	opf = BeautifulSoup(temptext, 'html.parser')
	
	itemrefs = opf.find_all('itemref')
	retlist = []
	for itemref in itemrefs:
		retlist.append(itemref['idref'])

	# while we're here, also grab the book title
	dctitle = opf.find('dc:title')
	if dctitle is not None:
		global worktitle
		worktitle = dctitle.string

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


def get_place(soup: BeautifulSoup) -> Position:
	bod = soup.body
	try:
		epubtype = bod['epub:type']
	except KeyError:
		return Position.NONE
	if 'backmatter' in epubtype:
		return Position.BACK
	elif 'frontmatter' in epubtype:
		return Position.FRONT
	elif 'bodymatter' in epubtype:
		return Position.BODY
	else:
		return Position.NONE


def add_landmark(soup: BeautifulSoup, textf: str, landmarks: list):
	epubtype = get_epub_type(soup)
	title = soup.find('title').string
	landmark = LandmarkItem()
	landmark.title = title
	if epubtype != '':
		landmark.epubtype = epubtype
		landmark.filelink = textf
		landmark.place = get_place(soup)
		landmarks.append(landmark)


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

		toprint = ''

		# check to see if next item is at same, lower or higher level than us
		if nextitem.level == thisitem.level:  # SIMPLE
			toprint += indent(thisitem.level) + '<li>\n'
			toprint += indent(thisitem.level) + thisitem.output()
			toprint += indent(thisitem.level) + '</li>\n'

		if nextitem.level > thisitem.level:  # PARENT
			toprint += indent(thisitem.level) + '<li>\n'
			toprint += indent(thisitem.level) + thisitem.output()
			toprint += indent(thisitem.level) + tabs(1) + '<ol>\n'
			unclosed_ol += 1
			if verbose:
				print(thisitem.filelink + ' unclosed ol = ' + str(unclosed_ol))

		if nextitem.level < thisitem.level:  # LAST CHILD
			toprint += indent(thisitem.level) + '<li>\n'
			toprint += indent(thisitem.level) + thisitem.output()
			toprint += indent(thisitem.level) + '</li>\n'  # end of this item
			torepeat = thisitem.level - nextitem.level
			current_level = thisitem.level
			if torepeat > 0:
				for _ in range(0, torepeat):  # need to repeat a few times as may be jumping back from eg h5 to h2
					toprint += indent(current_level, -1) + '</ol>\n'  # end of embedded list
					unclosed_ol -= 1
					if verbose:
						print(thisitem.filelink + ' unclosed ol = ' + str(unclosed_ol))
					toprint += indent(current_level, -2) + '</li>\n'  # end of parent item
					current_level -= 1

		tocfile.write(toprint)

	while unclosed_ol > 0:
		tocfile.write(tabs(3) + '</ol>\n')
		unclosed_ol -= 1
		if verbose:
			print('Closing: unclosed ol = ' + str(unclosed_ol))
		tocfile.write(tabs(2) + '</li>\n')


def output_toc(item_list: list, landmark_list, outtocpath: str):
	"""
	outputs the contructed ToC based on the lists of items  and landmarks found, to the specified output file
	"""
	if len(item_list) < 2:
		print('Too few ToC items found')
		return
	try:
		if os.path.exists(outtocpath):
			os.remove(outtocpath)  # get rid of file if it already exists
		tocfile = open(outtocpath, 'a', encoding='utf-8')
	except IOError:
		print('Unable to open output file! ' + outtocpath)
		return
	write_toc_start(tocfile)
	process_items(item_list, tocfile)
	write_toc_middle(tocfile)
	process_landmarks(landmark_list, tocfile)
	write_toc_end(tocfile)

	tocfile.close()


def write_toc_start(tocfile):
	"""
	write opening part of ToC
	"""
	tocfile.write('<?xml version="1.0" encoding="utf-8"?>\n')
	tocfile.write('<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" ')
	tocfile.write('epub:prefix="z3998: http://www.daisy.org/z3998/2012/vocab/structure/, ')
	tocfile.write('se: https://standardebooks.org/vocab/1.0" xml:lang="en-US">\n')
	tocfile.write(tabs(1) + '<head>\n')
	tocfile.write(tabs(2) + '<title>Table of Contents</title>\n')
	tocfile.write(tabs(1) + '</head>\n')
	tocfile.write(tabs(1) + '<body epub:type="frontmatter">\n')
	tocfile.write(tabs(2) + '<nav epub:type="toc">\n')
	tocfile.write(tabs(3) + '<h2 epub:type="title">Table of Contents</h2>\n')
	tocfile.write(tabs(3) + '<ol>\n')


def write_toc_middle(tocfile):
	"""
	write middle part of ToC and start of Landmarks
	"""
	tocfile.write(tabs(3) + '</ol>\n')
	tocfile.write(tabs(2) + '</nav>\n')
	tocfile.write(tabs(2) + '<nav epub:type="landmarks">\n')
	tocfile.write(tabs(3) + '<h2 epub:type="title">Landmarks</h2>\n')
	tocfile.write(tabs(3) + '<ol>\n')


def write_toc_end(tocfile):
	"""
	write closing part of ToC
	"""
	tocfile.write(tabs(3) + '</ol>\n')
	tocfile.write(tabs(2) + '</nav>\n')
	tocfile.write(tabs(1) + '</body>\n')
	tocfile.write('</html>')


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
		if verbose:
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
					if verbose:
						print(textf + ": ignoring noteref in heading")
				else:
					tocitem.title = extract_strings(child)
			else:  # should be a simple NavigableString
				accumulator += str(child)
	if tocitem.title == '':
		tocitem.title = accumulator


# FRONTMATTER_TYPES = ['titlepage', 'imprint', 'dedication', 'epigraph', 'abstract', 'preface', 'introduction', 'preamble', 'foreword']
# BACKMATTER_TYPES = ['afterword', 'appendix', 'acknowledgements', 'loi', 'rearnotes', 'endnotes', 'conclusion', 'glossary', 'colophon', 'copyright-page']


def process_all_content(filelist, textpath):
	toclist = []
	landmarks = []
	nest_under_halftitle = False
	for textf in filelist:
		if verbose:
			print('Processing: ' + textf)
		html_text = gethtml(os.path.join(textpath, textf))
		soup = BeautifulSoup(html_text, 'html.parser')
		place = get_place(soup)
		if place == Position.BACK:
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
	return landmarks, toclist


def main():
	"""
	main routine of the tool
	"""
	parser = argparse.ArgumentParser(description="Attempts to build a table of contents for an SE project")
	parser.add_argument("-o", "--output", dest="output", required=False, help="path and filename of output file if existing ToC is to be left alone")
	parser.add_argument("-v", "--verbose", required=False, action="store_const", const=True, help="verbose output")
	parser.add_argument("-n", "--nonfiction", required=False, action="store_const", const=True, help="work type is non-fiction")
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
	if args.nonfiction:
		worktype = 'non-fiction'
	else:
		worktype = 'fiction'

	global verbose
	verbose = args.verbose

	landmarks, toclist = process_all_content(filelist, textpath)

	outpath = tocpath
	if args.output != '':
		outpath = args.output
	output_toc(toclist, landmarks, outpath)
	print('done!')


if __name__ == "__main__":
	main()
