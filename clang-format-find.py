#!/usr/bin/env python

import sys, subprocess, difflib, copy

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
    'DerivePointerBinding',
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
}

INT_OPTS = {
    'AccessModifierOffset': [-1, -2, -4],
    'ColumnLimit': [0, 80, 100, 120],
    'ConstructorInitializerIndentWidth': [4],
    'ContinuationIndentWidth': [4],
    'IndentWidth': [1, 2, 4, 8],
    'MaxEmptyLinesToKeep': [1, 2],
    'PenaltyBreakBeforeFirstCallParameter': [1, 19],
    'PenaltyBreakComment': [60],
    'PenaltyBreakFirstLessLess': [120],
    'PenaltyBreakString': [1000],
    'PenaltyExcessCharacter': [1000000],
    'PenaltyReturnTypeOnItsOwnLine': [60, 200],
    'SpacesBeforeTrailingComments': [1, 2],
    'TabWidth': [2, 4, 8],
}

ALL_OPTS = BOOL_OPTS | set(ENUM_OPTS) | set(INT_OPTS)
CASES = sum([
    len(BOOL_OPTS) * 3,
    sum(len(v) + 1 for v in ENUM_OPTS.values()),
    sum(len(v) + 1 for v in INT_OPTS.values()),
])

def llvm():

    args = ['clang-format', '--dump-config', '--style=LLVM']
    proc = subprocess.Popen(args, stdout=subprocess.PIPE)
    ret = proc.wait()

    opts = {}
    for ln in proc.stdout.read().splitlines():
        if ln and ln[0].isalpha() and ln[0].isupper():
            key, val = ln.strip().split(':', 1)
            opts[key] = val.strip()

    return opts

def run(fn, opts, verbose=None):

    style = ',\n'.join('%s: %s' % (k, v) for (k, v) in sorted(opts.items()))
    args = ['clang-format', '-style={%s}' % style, fn]
    if verbose:
        print >> sys.stderr, ' '.join(args)

    proc = subprocess.Popen(args, stdout=subprocess.PIPE)
    ret = proc.wait()
    return proc.stdout.read()

def filescore(fn, opts, verbose=None):

    with open(fn) as f:
        old = f.read()
    new = run(fn, opts, verbose)

    res = 0
    for ln in difflib.unified_diff(old.splitlines(), new.splitlines()):

        if ln.startswith('---') or ln.startswith('+++') or ln.startswith('@'):
            continue

        if ln[0] in {'-', '+'}:
            res += 1

    return res

def score(files, opts, verbose=None):
    res = 0
    for fn in files:
        res += filescore(fn, opts, verbose)
    return res

def show_progress(rel):
    done = ('=' * int(round(70 * rel)))[:-1] + '>'
    left = ' ' * int(round(70 * (1 - rel)))
    sys.stderr.write('\r')
    sys.stderr.write('[%s%s] %3s%%' % (done, left, int(round(rel * 100))))
    sys.stderr.flush()

def main(args):

    verbose = False
    if '-v' in args:
        args.remove('-v')
        verbose = True

    if not args:
        print 'no files passed'
        return

    idx = 0
    best = llvm()
    base = score(args, best)
    for opt in sorted(ALL_OPTS):

        if opt in BOOL_OPTS:
            values = None, 'true', 'false'
        elif opt in ENUM_OPTS:
            values = [None] + list(ENUM_OPTS[opt])
        elif opt in INT_OPTS:
            values = [None] + list(INT_OPTS[opt])

        for val in values:

            idx += 1
            if not verbose:
                show_progress(idx / float(CASES))

            opts = copy.copy(best)
            if val is not None:
                opts[opt] = val
            else:
                opts.pop(opt, None)

            test = score(args, opts, verbose)
            if test < base:
                best[opt] = val

    print >> sys.stderr
    print '# Best configuration found'
    for k, v in sorted(best.iteritems()):
        print '%s: %s' % (k, v)

if __name__ == '__main__':
    main(sys.argv[1:])
