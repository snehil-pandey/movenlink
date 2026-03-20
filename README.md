# movenlink

A lightweight CLI tool to move applications across drives on Windows without breaking them.

It relocates folders and replaces them with symbolic links, so apps continue working as if nothing changed.

---

## Features

- Safe folder relocation (copy → verify → delete → link)
- Reverse operation (restore original location)
- Metadata tracking per folder
- Autocomplete support (Windows)
- Zero heavy dependencies
- Designed for low-end systems

---

## Why?

Windows applications often break when moved manually.  
movenlink solves this by using symbolic links to preserve original paths.

---

## Installation

```bash
git clone https://github.com/snehil-pandey/movenlink.git
cd movenlink
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt