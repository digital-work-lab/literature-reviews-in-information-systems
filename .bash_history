git config user.name "Gerit Wagner"
git config user.email "gerit.wagner@uni-bamberg.de"
quarto publish gh-pages
exit
git config --global user.name "Gerit Wagner"
git config --global user.email "gerit.wagner@uni-bamberg.de"
quarto publish gh-pages
ls
git remote -v
git config --global --add safe.directory /project
git remote -v
git config --global user.name "Gerit Wagner"
git config --global user.email "gerit.wagner@uni-bamberg.de"
quarto publish gh-pages
mkdir -p ~/.ssh
ssh-keyscan github.com >> ~/.ssh/known_hosts
quarto publish gh-pages
git status
git remote -v
quarto publish gh-pages
exit
