# Getting Started
!!! warning Nix is not your typical package manager that you can pick it up and just use it and hope for the best. It's really
  important to learn Nix the language first.

!!! note These instructions are meant for none NixOS users. If you're using NixOS, you already know what you're doing. Just
  enable our private binary cache and you're all set.

## Long version

If you are coming from a background of using traditional package managers like `apt`, `yum`, `pacman`, or `brew`, Nix offers a different approach to
package management that emphasizes reproducibility, isolation, and immutability. Understanding the core concepts and differences will help you adapt
to Nix more effectively.

### Key Concepts for Traditional Package Manager Users

1. **Functional Package Management**:
   - Traditional package managers work in an imperative way—installing, updating, or removing packages based on direct commands. Nix, on the other hand,
   follows a **functional paradigm** where packages and environments are defined declaratively.

   - Instead of manually managing dependencies and installations, you declare your desired state, and Nix ensures the system matches that state.

2. **Nix Store and Derivations**:
   - Nix uses a central storage location called the **Nix store** (`/nix/store`), where all packages are stored in unique directories identified by cryptographic hashes.
   - Each package in Nix is a **derivation**, which is essentially a build recipe that includes all dependencies, ensuring that builds are isolated and reproducible.

3. **Immutable Package Management**:
   - Packages installed by Nix are **immutable**, meaning they do not change once they are built. If you install a new version of a package, Nix keeps the old version
   intact, allowing you to switch back if needed.
   - Unlike traditional package managers, there is no concept of "upgrading" a package in-place; each new version is a separate derivation.

4. **Atomic Upgrades and Rollbacks**:
   - Traditional package managers may perform upgrades in a non-atomic way, meaning that failures in the middle of an upgrade can leave the system in a broken state.
   Nix guarantees that upgrades are atomic—either the entire operation succeeds, or nothing changes.

   - Rolling back to a previous state is straightforward with Nix, as every change is stored as a separate generation that you can revert to.

5. **Declarative vs. Imperative Configuration**:
   - With traditional package managers, you manage packages imperatively, installing or removing them as needed. Nix encourages **declarative configuration**
   through the use of a configuration file (usually `configuration.nix` or `default.nix`), where the entire system's desired state is declared.

   - You define what you want in your system, and Nix handles the rest—ensuring that your system matches the defined state.

6. **Isolated Development Environments (nix-shell, nix shell)**:
   - Traditional package managers often require virtual environments, Docker containers, or VMs to isolate environments. Nix provides **`nix-shell`**, which allows
   you to create isolated development environments with specific dependencies without polluting your global system environment.

   - These environments are defined in `shell.nix` files and can be shared and reproduced exactly on any machine with Nix installed.

## How Nix Works Compared to Traditional Package Managers

| Feature                         | Traditional Package Managers (apt, yum, brew, etc.) | Nix                                                       |
|---------------------------------|------------------------------------------------------|-----------------------------------------------------------|
| **Installation Model**          | Imperative (direct commands for install/remove)      | Declarative (define desired state, and Nix enforces it)   |
| **Dependency Handling**         | Can lead to "dependency hell" and conflicts          | Purely functional with isolated dependencies              |
| **Isolation**                   | Manual isolation through VMs or containers           | Built-in isolated environments via `nix-shell`            |
| **Upgrades/Rollbacks**          | Non-atomic upgrades, manual rollbacks                | Atomic upgrades with easy rollbacks using generations     |
| **Package Mutability**          | Packages are mutable and can be overwritten          | Packages are immutable; new versions are separate         |
| **Multi-user Environment**      | Shared package database; risk of conflicts            | Multiple users can safely share the Nix store             |
| **Consistency Across Systems**  | Dependent on environment; may vary                   | Fully reproducible builds and environments                |
| **Learning Curve**              | Easier to get started; familiar syntax and commands  | Steeper learning curve; requires understanding Nix language and concepts |

## Conclusion

For users familiar with traditional package managers, Nix may present a steeper learning curve, but the benefits of reproducibility, isolation, and reliability are significant.
Nix changes the way you think about package management and system configuration, providing a more deterministic and controlled approach.

### Things to Keep in Mind When Switching to Nix

- Embrace the **functional mindset**: Understand that packages are defined declaratively and builds are isolated and reproducible.
- Learn about `nix` the language and different toolings that it provides for creating reproducible development environments.
- Get comfortable with **atomic upgrades and rollbacks**, as they provide safety nets for your system.

### Installing Nix
In order to install `nix` you have two options: multi-user or single-user modes.

** I highly recomment to install nix in single-user mode, since it's pretty straight forward.**

You can learn how to install `nix` by using the [official documentation](https://nixos.org/download/).

### Setting up Nix
After installing nix what you need to do is to enable our private cache alongside the public cache.
To do so, first copy/paste the following configuration in your `cat ~/.config/nix/nix.conf` file:

```ini
trusted-public-keys = nix-community.cachix.org-1:mB9FSh9qf2dCimDSUo8Zy7bkq5CX+/rkCWyvRCYg3Fs= cache.nixos.org-1:6NCHdD59X431o0gWypbMrAURkbJ16ZPMQFGspcDShjY= cache.plex.bz:Vdh+jRJPqfHyL3Mq5fHqRVMOoI3Jg6eSXkafBgY2eRU=
trusted-substituters = https://nix-community.cachix.org https://cache.nixos.org https://cache.plex.bz
trusted-users = root @wheel

experimental-features = nix-command flakes
```
!!! warning Nix will not use our binary cache if you don't setup the public key correctly.


and then make sure to setup your `awscli` configuration with your correct `aws_access_key_id` and `aws_secret_access_key`.

Copy the folliwing configuration in your `~/.aws/config`:
```toml
[default]
region = us-east-1
role_session_name = nix_<YOUR_USERNAME>
role_arn = arn:aws:iam::362267952554:role/nix-binary-cache-user
source_profile = default
```
!!! note If you don't have access to aws, ask the infra team.

!!! note The above snippet, is for the default aws profile, if you need to change the profile to something else,
  make sure to user `profile=NAME_OF_THE_PROFILE` querystring whenever you provide a cache url for nix.

## Short version
### Further Reading

- [Nix Manual](https://nixos.org/manual/nix/stable/)
- [Getting Started with Nix and Nixpkgs](https://nixos.org/manual/nixpkgs/stable/)
- [Comparison of Nix with Other Package Managers](https://nixos.org/guides/comparisons.html)
