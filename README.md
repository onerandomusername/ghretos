# ghretos

<sup>the name was off the cuff, consider [suggesting][issues] a new one</sup>

Ghretos exists to take a GitHub source URL and parse it into the resource that it points to. Whereas the GitHub API provides an `html_url` for every object, Ghretos aims to provide a parsed object for each `html_url`. While Ghretos is still very much in beta, it is used in [Monty Python], my Discord Bot, to power the detection of GitHub URLs in Discord messages and replace them with actually useful embeds.

[issues]: https://github.com/onerandomusername/ghretos/issues/new/choose
[Monty Python]: https://github.com/onerandomusername/monty-python/pull/738

## How it works

Use ``parse_url`` to retrieve a ghretos.GitHubResource from an arbitrary URL. If the URL does not match, ``None`` will be returned.

If you wish to have control over what parse_url matches, you can provide a ``MatcherSettings`` object to parse_url which will be used to control what objects are matched.
This can be useful if you have only implemented support for a specific number of GitHub resources.
By default, all supported GitHub source URLs are matched.

## Todo

- [ ] Full support for GHES and GHEC
- [ ] Provide api.github.com and equivalent URLs on matched objects (when possible) for full reversal
- [ ] Potential integration with [githubkit][].

[githubkit]: https://pypi.org/p/githubkit


## Links

The documentation can be found at [readthedocs][rtd].


[rtd]: https://ghretos.readthedocs.io
