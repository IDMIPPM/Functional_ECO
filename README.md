# Functional ECO

Python tool for functional ECO Patch Generation. Tool was prepared for ICCAD 2017 contest.

# Usage

`python ./eco_flow.py <F.v> <G.v> <weight.txt> <patch.v> <out.v>`

## Example:

```bash
mkdir results
python ./eco_flow.py testcases/unit1/F.v testcases/unit1/G.v testcases/unit1/weight.txt results/patch.v results/out.v
```

# Requirements

Code requires ABC binary for functional verification

**Linux**: You need to compile ABC (see instruction below)

**Windows**: ABC binary already included

# Linux ABC installation

```bash
hg clone https://bitbucket.org/alanmi/abc
cd abc
make
cp abc ../equiv_check/linux/abc.exe
```

**Note**: it's recommended to replace line "OPTFLAGS  ?= -g -O" in abc Makefile with "OPTFLAGS  ?= -g -O3" for faster code.
