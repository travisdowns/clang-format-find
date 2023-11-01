#!/usr/bin/env python3

import argparse
from pathlib import Path
import sys
import subprocess
import difflib
import copy
from typing import Any, Optional

import yaml

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
    'AlignAfterOpenBracket':
    ['Align', 'DontAlign', 'AlwaysBreak', 'BlockIndent'],
    'AlignArrayOfStructures': ['Left', 'Right', 'None'],
    'PointerAlignment': ['Left', 'Right', 'Middle'],
    'EmptyLineBeforeAccessModifier':
    ['Never', 'Leave', 'LogicalBlock', 'Always'],  # clang-13
    'EmptyLineAfterAccessModifier': ['Never', 'Leave', 'Always']  # clang-13
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

ALL_OPTS = BOOL_OPTS | set(ENUM_OPTS) | set(INT_OPTS)
CASES = sum([
    len(BOOL_OPTS) * 3,
    sum(len(v) + 1 for v in ENUM_OPTS.values()),
    sum(len(v) + 1 for v in INT_OPTS.values()),
])


class ClangFormat:

    def __init__(self, argv: list[str]):
        parser = argparse.ArgumentParser()
        parser.add_argument('files',
                            help='One or more files to analyze',
                            metavar='FILES',
                            nargs='+')
        parser.add_argument(
            '--based-on',
            help='Specify a single based on style to start the search',
            choices=ALL_STYLES,
            type=str)
        parser.add_argument(
            '--score-only',
            help=
            'Just score the given clang-format config file againt the passed files',
            type=Path)
        parser.add_argument('-v',
                            help='Enable verbose mode',
                            action='store_true')
        args = parser.parse_args(argv[1:])

        self.file_list: list[str] = args.files
        self.base_styles = [str(args.based_on)
                            ] if args.based_on else ALL_STYLES
        self.score_only: Optional[Path] = args.score_only
        self.verbose = args.v

    def run_inner(self, args: list[str]):
        args = ['clang-format'] + args
        if self.verbose:
            print('\n', ' '.join(args), file=sys.stderr)
        proc = subprocess.Popen(args, stdout=subprocess.PIPE)
        assert proc.stdout
        stdout = proc.stdout.read().decode()
        ret = proc.wait()
        if ret != 0:
            raise RuntimeError(f'Failed to run clang-format command:\n' +
                               ' '.join([f"'{a}'" for a in args]))
        return stdout

    def dump_config(self, style: str):

        stdout = self.run_inner(['--dump-config', f'--style={style}'])

        opts: ConfigType = {}
        for ln in stdout.splitlines():
            if ln and ln[0].isalpha() and ln[0].isupper():
                key, val = ln.strip().split(':', 1)
                opts[key] = val.strip()

        return opts

    def run(self, filenames: list[str], opts: ConfigType):

        style = ',\n'.join('%s: %s' % (k, v)
                           for (k, v) in sorted(opts.items()))

        return self.run_inner(['-style={%s}' % style] + filenames)

    def filescore(self, filename: list[str], opts: ConfigType):

        all_text: list[str] = []

        for f in filename:
            all_text += (Path(f).read_text().splitlines())

        new = self.run(filename, opts)

        res = 0
        for ln in difflib.unified_diff(all_text, new.splitlines()):

            if ln.startswith('---') or ln.startswith('+++') or ln.startswith(
                    '@'):
                continue

            if ln[0] in {'-', '+'}:
                res += 1

        if self.verbose:
            print('Score: ', res)

        return res

    def show_progress(self, rel: float, label: str):
        pct = round(rel * 100, ndigits=1)
        if self._last_pct != pct:
            done = ('=' * int(round(70 * rel)))[:-1] + '>'
            left = ' ' * int(round(70 * (1 - rel)))

            sys.stderr.write('\r')
            sys.stderr.write(f'[{done}{left}] {pct:5.1f}% {label} ')
            sys.stderr.flush()
        self._last_pct = pct

    def main(self):

        self._last_pct = -1.

        file_list = self.file_list

        if not file_list:
            print('no files passed', file=sys.stderr)
            exit(1)

        if self.score_only:
            t = self.score_only.read_text()
            opts = yaml.safe_load(t)
            # need to replace True and False with lowercase strings
            for k, v in opts.items():
                if v is True or v is False:
                    opts[k] = 'true' if v else 'false'
            score = self.filescore(file_list, opts)
            print(f'Score: {score}')
            return

        for based_on in self.base_styles:
            idx = 0
            # best = dump_config(initial_style)
            best: ConfigType = {'BasedOnStyle': based_on}
            best_score = self.filescore(file_list, best)
            if self.verbose:
                print('Base score: ', best_score)
            allopts = ALL_OPTS
            for opt in sorted(allopts):

                if opt in BOOL_OPTS:
                    values = None, 'true', 'false'
                elif opt in ENUM_OPTS:
                    values = [None] + list(ENUM_OPTS[opt])
                elif opt in INT_OPTS:
                    values = [None] + list(INT_OPTS[opt])
                else:
                    raise RuntimeError(f'bad opt: {opt}')

                for val in values:

                    idx += 1
                    if not self.verbose:
                        label = f'best: {best_score} ({based_on})'
                        self.show_progress(idx / float(CASES), label)

                    opts = copy.copy(best)
                    if val is not None:
                        opts[opt] = val
                    else:
                        opts.pop(opt, None)

                    cur_score = self.filescore(file_list, opts)
                    if cur_score < best_score:
                        best[opt] = val
                        best_score = cur_score

            print('', file=sys.stderr)
            print(f'# Best configuration found based on: {based_on}')
            print('# Score: %d' % best_score)
            for k, v in sorted(best.items()):
                print('%s: %s' % (k, v))


if __name__ == '__main__':
    ClangFormat(sys.argv).main()
