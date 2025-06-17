
# How do I contribute?

Nixer is designed to be extremely modular, so often, you don't have to.

Nonetheless, some changes can only be made here.

Step 1. Look for an open or closed issue. This may be the quickest path to a solution to your problem.

Step 2. If needed, open an issue. This way we can discuss the problem, and if necessary discuss changes, if any need to be made.

Step 3. If needed, create a PR. Make sure to run `nixpkgs-fmt`on your code.


# Style

This repository is written in a style similar to that of Nixpkgs, with some exceptions.
The following sections describe such additions, exceptions, and it probably confirms some rules.

## Camel case


 - File names may be in camelCase. This reduces the number of unique names in the project.

Except for file names, the Nixpkgs casing rule is maintained here as well:

 - Package names are verbatim or in snake-case. Example:
    - `flake-parts-lib`

 - Functionality provided by flake-parts is in camelCase. Examples:
    - `getSystem`
    - `mkFlake`

## Rule #1. Go with the flow

Write code that fits in. Don't reformat existing code. Don't obsess over fitting in. Write good docs and tests instead.

## Rule #2

Backward compatibility is the king.
