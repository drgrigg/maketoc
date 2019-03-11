#!/usr/bin/env python3
"""
routine which tries to create a valid table of contents file for SE projects
"""
import argparse
import os
from typing import TextIO

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

	def output(self) -> str:
		"""
		the output method just outputs the linking tag line eg <a href=... depending on the data found
		"""
		outstring = ''

		# there are LOTS of combinations to deal with!
		if self.subtitle == '':  # no subtitle
			if self.roman != '':
				outstring += '\t<a href="text/' + self.filelink + '" epub:type="z3998:roman">' + self.roman + '</a>\n'
			else:
				outstring += '\t<a href="text/' + self.filelink + '">' + self.title + '</a>\n'
		else:  # there is a subtitle
			if self.roman != '':
				outstring += '\t<a href="text/' + self.filelink + '">' + '<span epub:type="z3998:roman">' + self.roman + '</span>: ' + self.subtitle + '</a>\n'
			else:
				outstring += '\t<a href="text/' + self.filelink + '">' + self.title + ': ' + self.subtitle + '</a>\n'

		return outstring


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


def read_toc_start_and_end(tocpath: str) -> list:
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


def output_toc(item_list: list, tocpath: str, outtocpath: str):
	"""
	outputs the contructed ToC based on the list of items found, to the specified output file
	"""
	if len(item_list) < 2:
		print('Too few ToC items found')
		return

	startends = read_toc_start_and_end(tocpath)  # this returns a list of lists (start and end)

	try:
		if os.path.exists(outtocpath):
			os.remove(outtocpath)  # get rid of file if it already exists
		tocfile = open(outtocpath, 'a', encoding='utf-8')
	except IOError:
		print('Unable to open output file! ' + outtocpath)
		return

	for line in startends[0]:  # this is the starting part of existing ToC
		tocfile.write(line)

	process_items(item_list, tocfile)

	for line in startends[1]:  # this is the ending part of the existing ToC file
		tocfile.write(line)

	tocfile.close()


def get_parent_id(hchild: Tag) -> str:
	"""
	climbs up the document tree looking for parent id in a <section> tag.
	"""
	dad = hchild.find_parent("section")
	if dad is None:
		return ''
	try:
		return dad['id']
	except KeyError:
		return ''


def extract_strings(child: Tag) -> str:
	"""
	returns the string content only of a tag (ignores embedded <abbr> etc)
	"""
	retstring = ''
	for string in child.strings:
		retstring += string
	return retstring


def process_headings(soup: BeautifulSoup, textf: str, toclist: list, nest_under_halftitle: bool):
	"""
	find headings in current file and extract data into items added to toclist
	"""
	# find all the h1, h2 etc headings
	heads = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])

	if len(heads) == 0:  # may be a dedication or an epigraph, etc with no heading tag
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


def process_heading(heading, is_toplevel, textf):
	tocitem = TocItem()
	parent_sections = heading.find_parents('section')
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
	# a heading may include epub:type directly, eg <h5 epub:type="title z3998:roman">II</h5>
	try:
		attribs = heading['epub:type']
		if 'z3998:roman' in attribs:
			tocitem.roman = extract_strings(heading)
	except KeyError:
		print(textf + ': warning: heading with no epub:type')
	accumulator = ''
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
	return tocitem


BACKMATTER_FILENAMES = ["endnotes.xhtml", "loi.xhtml", "afterword.xhtml", "appendix.xhtml", "colophon.xhtml", "uncopyright.xhtml", "glossary.xhtml"]


def main():
	"""
	main routine of the tool
	"""
	parser = argparse.ArgumentParser(description="Attempts to build a table of contents for an SE project")
	parser.add_argument("-o", "--output", dest="output", required=False, help="path and filename of output file if existing ToC is to be left alone")
	parser.add_argument("directory", metavar="DIRECTORY", help="a Standard Ebooks source directory")
	args = parser.parse_args()

	rootpath = args.directory
	tocpath = os.path.join(rootpath, 'src', 'epub', 'toc.xhtml')
	textpath = os.path.join(rootpath, 'src', 'epub', 'text')
	opfpath = os.path.join(rootpath, 'src', 'epub', 'content.opf')
	filelist = getcontentfiles(opfpath)

	toclist = []

	nest_under_halftitle = False

	for textf in filelist:
		html_text = gethtml(os.path.join(textpath, textf))
		soup = BeautifulSoup(html_text, 'html.parser')
		if textf in BACKMATTER_FILENAMES:
			nest_under_halftitle = False
		process_headings(soup, textf, toclist, nest_under_halftitle)
		if textf == 'halftitle.xhtml':
			nest_under_halftitle = True

	# we add this dummy item because outputtoc always needs to look ahead to the next item
	lasttoc = TocItem()
	lasttoc.level = 1
	lasttoc.title = "dummy"
	toclist.append(lasttoc)

	outpath = tocpath
	if args.output != '':
		outpath = args.output
	output_toc(toclist, tocpath, outpath)
	print('done!')


if __name__ == "__main__":
	main()
