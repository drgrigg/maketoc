# maketoc
Python routine to create table of contents for SE projects

This attempts to create a valid table of contents file for Standard Ebooks projects.

## Usage:

`maketoc.py PROJECT_DIRECTORY [-v] [-n] [-o OUTPUT_FILEPATH]`

-v: verbose  
-n: declares the book as non-fiction (default is fiction)  
-o: outputs to a separate file, doesn't overwrite existing ToC

It assumes:

- print-manifest-and-spine has been run on the project
- spine has been manually sorted into the correct order
- content files have correctly had `<section>` tags applied
- content files have correct `<title>` tags.

It works by examining the spine and processing each file in the spine in order, 
looking for sections and heading tags (h2, h3, etc) and building a list of them with required info.
It then processes this list to output the ToC items.

Note that it reads any existing toc.xhtml and rewrites the list of items and landmarks.

A sample ToC file generated from a very complex project is included in the repository as testToc.xhtml.
