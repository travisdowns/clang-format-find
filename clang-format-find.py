#!/usr/bin/env python3

import sys
import subprocess
import difflib
import copy
from typing import Any

ConfigType = dict[str, Any]

BOOL_OPTS = {
    'AlignEscapedNewlinesLeft',
    'AlignTrailingComments',
    'AllowAllParametersOfDeclarationOnNextLine',
    'AllowShortIfStatementsOnASingleLine',
    'AlwaysBreakBeforeMultilineStrings',
    'AlwaysBreakTemplateDeclarations',
    'BinPackParameters',
    'BreakBeforeBinaryOperators',
    'BreakBeforeTernaryOperators',
    'BreakConstructorInitializersBeforeComma',
    'Cpp11BracedListStyle',
    'IndentCaseLabels',
    'IndentFunctionDeclarationAfterType',
    'ObjCSpaceBeforeProtocolList',
    'PointerBindsToType',
    'SpaceBeforeAssignmentOperators',
    'SpaceInEmptyParentheses',
    'SpacesInAngles',
    'SpacesInCStyleCastParentheses',
    'SpacesInParentheses',
}

ENUM_OPTS = {
    'BreakBeforeBraces': ['Attach', 'Linux', 'Stroustrup', 'Allman'],
    'NamespaceIndentation': ['None', 'Inner', 'All'],
    'Standard': ['Cpp03', 'Cpp11', 'Auto'],
    'UseTab': ['Never', 'ForIndentation', 'Always'],
    'PointerAlignment': ['Left', 'Right', 'Middle']
}

INT_OPTS = {
    'AccessModifierOffset': [-1, -2, -4],
    'ColumnLimit': [0, 80, 100, 120],
    'ConstructorInitializerIndentWidth': [4],
    'ContinuationIndentWidth': [4],
    'IndentWidth': [1, 2, 4, 8],
    'MaxEmptyLinesToKeep': [1, 2, 3, 4, 5, 6],
    'PenaltyBreakBeforeFirstCallParameter': [1, 19],
    'PenaltyBreakComment': [60],
    'PenaltyBreakFirstLessLess': [120],
    'PenaltyBreakString': [1000],
    'PenaltyExcessCharacter': [1000000],
    'PenaltyReturnTypeOnItsOwnLine': [60, 200],
    'SpacesBeforeTrailingComments': [1, 2],
    'TabWidth': [2, 4, 8],
}

ALL_STYLES = [
    'LLVM', 'Google', 'Chromium', 'Mozilla', 'WebKit', 'Microsoft', 'GNU'
]

BASED_ON_STYLE = {'BasedOnStyle': ALL_STYLES}

ALL_OPTS = BOOL_OPTS | set(ENUM_OPTS) | set(INT_OPTS)
CASES = sum([
    len(BOOL_OPTS) * 3,
    sum(len(v) + 1 for v in ENUM_OPTS.values()),
    sum(len(v) + 1 for v in INT_OPTS.values()),
])

class ClangFormat:

    def dump_config(self, style: str):

        args = ['clang-format', '--dump-config', f'--style={style}']
        proc = subprocess.Popen(args, stdout=subprocess.PIPE)
        ret = proc.wait()
        if ret != 0:
            print('clang-format call failed (output above)')
            sys.exit(1)

        opts = {}
        assert proc.stdout
        for ln in proc.stdout.read().splitlines():
            if ln and ln[0].isalpha() and ln[0].isupper():
                key, val = ln.strip().split(':', 1)
                opts[key] = val.strip()

        return opts


    def run(self, fn, opts):

        style = ',\n'.join('%s: %s' % (k, v) for (k, v) in sorted(opts.items()))
        args = ['clang-format', '-style={%s}' % style, fn]
        if self.verbose:
            print('\n\n', ' '.join(args), file=sys.stderr)

        proc = subprocess.Popen(args, stdout=subprocess.PIPE)
        stdout = proc.stdout.read().decode()
        ret = proc.wait()
        if ret != 0:
            raise RuntimeError(f'Failed to run clang-format command:\n' +
                            ' '.join([f"'{a}'" for a in args]))
        return stdout


    def filescore(self, filename: str, opts: ConfigType):

        with open(filename) as f:
            old = f.read()

        new = self.run(filename, opts)

        res = 0
        for ln in difflib.unified_diff(old.splitlines(), new.splitlines()):

            if ln.startswith('---') or ln.startswith('+++') or ln.startswith('@'):
                continue

            if ln[0] in {'-', '+'}:
                res += 1

        if self.verbose:
            print('Score: ', res)

        return res


    def score(self, files: list[str], opts: ConfigType):
        res = 0
        for fn in files:
            res += self.filescore(fn, opts)
        return res


    def show_progress(self, rel: float):
        done = ('=' * int(round(70 * rel)))[:-1] + '>'
        left = ' ' * int(round(70 * (1 - rel)))
        sys.stderr.write('\r')
        sys.stderr.write('[%s%s] %3s%%' % (done, left, int(round(rel * 100))))
        sys.stderr.flush()


    def main(self, args: list[str]):

        if '-v' in args:
            args.remove('-v')
            self.verbose = True
        else:
            self.verbose = False

        if not args:
            print('no files passed')
            return

        for based_on in ALL_STYLES:
            idx = 0
            # best = dump_config(initial_style)
            best: ConfigType = {'BasedOnStyle': based_on}
            base = self.score(args, best)
            if self.verbose:
                print('Base score: ', base)
            allopts = ALL_OPTS
            for opt in sorted(allopts):

                if opt in BOOL_OPTS:
                    values = None, 'true', 'false'
                elif opt in ENUM_OPTS:
                    values = [None] + list(ENUM_OPTS[opt])
                elif opt in INT_OPTS:
                    values = [None] + list(INT_OPTS[opt])
                elif opt in BASED_ON_STYLE:
                    values = list(BASED_ON_STYLE[opt])
                else:
                    raise RuntimeError(f'bad opt: {opt}')

                for val in values:

                    idx += 1
                    if not self.verbose:
                        self.show_progress(idx / float(CASES))

                    opts = copy.copy(best)
                    if val is not None:
                        opts[opt] = val
                    else:
                        opts.pop(opt, None)

                    test = self.score(args, opts)
                    if test < base:
                        best[opt] = val
                        base = test

            print('', file=sys.stderr)
            print(f'# Best configuration found based on: {based_on}')
            print('# Score: %d' % base)
            for k, v in sorted(best.items()):
                print('%s: %s' % (k, v))


if __name__ == '__main__':
    ClangFormat().main(sys.argv[1:])
