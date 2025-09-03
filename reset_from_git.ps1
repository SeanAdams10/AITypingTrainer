# 1. Ensure you're on the right branch
git checkout web-ready

# 2. Fetch the latest info from GitHub (without merging)
git fetch origin

# 3. Reset your local branch to match the remote branch exactly
git reset --hard origin/web-ready
