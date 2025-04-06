# bx Compiler Pipeline

This is a coursework project completed during university.  
Not all of this is my work, I first started with a template.

---

## Overview

This is a compiler implementation for a simple programming language called "bx".  
The compiler translates programs written in the bx language into x86-64 assembly code through several steps:

- **Front-end (`bx2front.py`)**  
  Parses bx source code and performs type checking

- **Three-Address Code (`bx2tac.py`)**  
  Converts the parsed code into Three-Address Code (TAC), an intermediate representation

- **Optimisation (`tac_cfopt.py`)**  
  Applies control flow optimisations to the TAC

- **Code Generation (`tac2x64.py`)**  
  Converts the optimised TAC into x86-64 assembly code

---

## To Run the Compiler

You need:

- A `.bx` source file (see examples folder)
- The main entry point: `bxcc.py`, which manages the entire compilation process

Make sure your `.bx` source file is in the same folder as `bxcc.py` (your current directory).  
Then, run:

```bash
$ python bxcc.py your_program.bx
```

This will:

- Parse and type-check the bx program  
- Generate a `.tac.json` file  
- Optimise the TAC (creates a `.tac_opt.json` file)  
- Generate an assembly file (`.s` file)

## To Execute the Compiled Program

Assemble and link the `.s` file

```bash
$ gcc -c your_program.s
```

Link:

```bash
$ gcc -o your_program your_program.o
```

Run the program:

```bash
$ ./your_program
```

## The bx Language Supports

- Variables of types `int` and `bool`
- Procedures with arguments
- Control structures like `if-else` and `while`
- Expressions including arithmetic, logic, and comparison operations
- A `print` function for output


## Complete Pipeline

The full compilation process flows like this:

- `bxcc.py` → Read source file (bx compiler collection)
- `scanner.py` → Convert source to tokens
- `parser.py` → Convert tokens to AST
- `bx2front.py` → Analyse and validate the AST (type checking)
- `bx2tac.py` → Convert AST to Three-Address Code
- `tac_cfopt.py` → Optimise the TAC
- `tac2x64.py` → Generate x86-64 assembly
- `bxcc.py` → Write the assembly to a file

