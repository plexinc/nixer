{ lib }:
{
  /*
  * Fetch the give repo `name` with the ginve `rev` and `ref` (default `main`)
  * from github using ssh.
  *
  * Any other parameter passed to this function will be passed to the
  * `builtins.fetchGit` function.
  */
  plexFetchFromGitHub = { repo, rev, ref ? "main", ... }:
    builtins.fetchGit {
      url = "https://github.com/plexinc/${repo}.git";
      shallow = true;
      inherit ref rev;
    };

}
