### clang-format-find

`clang-format-find` helps you find the clang-format style that best fits your
current code style, to help you more consistently apply your chosen style.

It does this by starting from the LLVM style included with `clang-format`,
iterating over a number of values for each option (including undefined),
then comparing the result by counting the size of a unified diff of the
original file contents to the formatted file results.

This is a fork of [the original](https://github.com/djc/clang-format-find) by
Dirkjan Ochtman, adding Python 3 support and some other fixes.
