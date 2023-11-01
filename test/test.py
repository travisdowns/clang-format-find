#!/usr/bin/env python3

# acceptance test for clang-format-find

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


class OneTest:

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
        file_name = test_name + '.txt'
        gold_out = (gold_dir / file_name).read_text().splitlines()
        actual_out = self.run_cff(args).splitlines()

        if actual_out != gold_out:
            print(f'TEST FAILED: {test_name}')
            diff = difflib.unified_diff(gold_out,
                                        actual_out,
                                        fromfile=f'gold/{test_name}',
                                        tofile=f'actual/{test_name}')
            print('\n'.join(list(diff)))
            # print(actual_out)

            return False

        print(f'TEST PASSED: {test_name}')
        return True

    class TestDef(NamedTuple):
        args: list[str]
        goldfile: str

    tests: list[TestDef] = [TestDef(all_srcs, 'test0')]

    def run_all(self):
        passed = 0
        for test in self.tests:
            if self.gold_test(test.args, test.goldfile):
                passed += 1

        print(f'{passed}/{len(self.tests)} tests passed')

        if passed != len(self.tests):
            sys.exit(1)


OneTest().run_all()
