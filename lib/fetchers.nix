{}:
{
  /*
  * Fetch the give repo `name` with the ginve `rev` and `ref` (default `main`)
  * from github using ssh.
  *
  * Any other parameter passed to this function will be passed to the
  * `builtins.fetchGit` function.
  */
  plexFetchFromGitHub = { name, rev, ref ? "main", ... }@params:
    builtins.fetchGit
      ({
        url = "ssh://git@github.com/plexinc/${name}.git";
        shallow = true;
        inherit ref rev;
      } // params);
}
