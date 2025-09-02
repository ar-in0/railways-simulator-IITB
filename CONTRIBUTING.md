# Contribution Guidelines
Collection of standard procedures to keep development organized.

## Resources
GIT tutorials sorted according to the time needed to complete them. The first one is the shortest. The last one ends with a summary of
useful commands while working on a shared github project.
1. [git - the simple guide by Roger Dudler](https://rogerdudler.github.io/git-guide/)  
2. [introduction to Git by GitHub](https://docs.github.com/en/get-started/git-basics/set-up-git)
3. [Typical GitHub Workflow on a shared project](https://neval8.wordpress.com/2013/07/07/en-typical-workflow-with-github-on-shared-project/)  

## Getting Started
Anyone with Git, a Github account and an internet connection can modify the codebase. To do so, your local machine must have a clone of your fork of the upstream repo. 
1. Fork this repo.  
2. Clone your fork to local machine via `git clone <forked-repo-url>`  
3. Set upstream repo via `git remote add upstream https://github.com/ar-in0/railways-simulator-IITB.git`  

To download the latest updates from upstream:
```bash
# Navigate to the project root directory
cd <wherever>

git fetch upstream

# view the latest changes
# This will give a detached HEAD state. Dont panic - just dont commit any changes to upstream/main
# From upstream/main you can either create a new branch for a new feature, or return to origin/main
git checkout upstream/main 
```
4. Configure git to push to your fork by default for new branches via `git config remote.pushDefault origin`  
5. **Add a brief summary of your task to the [README](README.md) (one per subgroup), using the [new feature workflow](#adding-a-new-featurebugfix) described below.**

## Adding a new feature/bugfix
The repo hosted at [ar-in0/railways-simulator-IITB](https://github.com/ar-in0/railways-simulator-IITB) is called *upstream*. Currently owned by Armaan.
- As soon as you decide to work on a bugfix/feature, **create a new branch** in your local repo. 
- Expect an always dirty forked main. Therefore branch from `upstream/main` always and not `origin/main`.

```bash
# New branch for new bug/feature, starting from upstream/main
# ensure you have the latest upstream version
git fetch upstream

# create and switch to a bugfix branch
git checkout -b <feature_xx_desc> upstream/main # new branch from upstream/main

# Make your local changes to the codebase

# local git commit
# and push to origin i.e. your fork
git add .
git commit 
git push
```

Once you have committed a change to your local feature/bugfix branch, 
merging your newer commit with upstream requires creation of a *pull request* based on the 
latest set of pushed commits. After `git push` above:
- Navigate to the *upstream* github repo.
- If new changes were recently pushed to the forked repo, 
you will see a message prompting you to make a new **pull request**.

> Once a new PR is created, armaan will review and merge the new branch into upstream. For this project, since commits will usually be made to
> files in independent directories, PRs will be assumed correct and always be approved for merge.

After a PR is merged into upstream, it is safe to delete your local feature branch. You may continue development in a newly created feature branch...
