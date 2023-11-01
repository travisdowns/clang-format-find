#!/usr/bin/env python3

# acceptance test for clang-format-find

import argparse
import difflib
import subprocess
from pathlib import Path
import sys
from typing import NamedTuple

test_dir = Path(__file__).parent.resolve()
gold_dir = test_dir / 'gold'
src_dir = test_dir / 'src'
root_dir = test_dir.parent

all_srcs = list(map(str, src_dir.glob('*.cpp')))
one_src = str(src_dir / 'perf-timer.cpp')


def splitlist(s: str):
    return s.split(',')


class TestDef(NamedTuple):
    args: list[str]
    goldfile: str


all_tests: list[TestDef] = [
    TestDef(all_srcs, 'test0'),
    TestDef([one_src], 'test1'),
    TestDef([one_src, '--based-on=LLVM'], 'test2'),
    TestDef([one_src, '--based-on=GNU'], 'test3'),
]


class OneTest:

    def __init__(self):

        parser = argparse.ArgumentParser()
        parser.add_argument('--tests',
                            help='Comma separated list of tests to run',
                            type=splitlist)
        parser.add_argument(
            '--write-goldfiles',
            help='''When a difference is found in the actual output compared to
            the expected output, update the goldfile with the actual output instead of failing the test.''',
            action='store_true')

        args = parser.parse_args()

        self.tests = [
            t for t in all_tests if not args.tests or t.goldfile in args.tests
        ]

        self.write: bool = args.write_goldfiles

    def run_cff(self, args: list[str]):
        args = [str(root_dir / 'clang-format-find.py')] + args
        try:
            output = subprocess.check_output(args, encoding='utf8')
        except subprocess.CalledProcessError as cpe:
            print(f'------ stdout of failed run -------\n{cpe.output}' +
                  '-' * 35)
            raise

        return output

    def gold_test(self, args: list[str], test_name: str):
        goldfile = gold_dir / (test_name + '.txt')
        try:
            gold_out = goldfile.read_text().splitlines()
        except FileNotFoundError:
            if not self.write:
                raise
            gold_out = ''  # allow writing of non-existent goldfiles to populate them initially

        actual_out = self.run_cff(args).splitlines()

        if actual_out != gold_out:
            if self.write:
                print(f'TEST FAILED (goldflie will be updated): {test_name}')
                goldfile.write_text('\n'.join(actual_out) + '\n')
            else:
                print(f'TEST FAILED: {test_name}')
                diff = difflib.unified_diff(gold_out,
                                            actual_out,
                                            fromfile=f'gold/{test_name}',
                                            tofile=f'actual/{test_name}')
                print('\n'.join(list(diff)))

            return False

        print(f'TEST PASSED: {test_name}')
        return True

    def run_all(self):
        passed = 0
        for test in self.tests:
            if self.gold_test(test.args, test.goldfile):
                passed += 1

        print(f'{passed}/{len(self.tests)} tests passed')

        if passed != len(self.tests):
            sys.exit(1)


OneTest().run_all()
