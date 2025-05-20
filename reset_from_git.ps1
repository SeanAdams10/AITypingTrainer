# 1. Ensure you're on the right branch
git checkout my-feature-branch

# 2. Fetch the latest info from GitHub (without merging)
git fetch origin

# 3. Reset your local branch to match the remote branch exactly
git reset --hard origin/my-feature-branch
