# maketoc
Python routine to create table of contents for SE projects

This attempts to create a valid table of contents file for Standard Ebooks projects.

It assumes:

- print-manifest-and-spine has been run on the project
- spine has been manually sorted into the correct order

It works by examining the spine and processing each file in the spine in order, 
looking for header tags (h2, h3, etc) and building a list of them with required info.
It then processes this list to output the ToC items.

Note that it reads any existing toc.xhtml and rewrites the list of items, leaving Landmarks untouched.

At present it doesn't do a very good job of indenting the items (this is on the TODO list!)

A sample ToC file generated from a very complex project is included in the repository as testToc.xhtml.
