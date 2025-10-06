HOME=/home/coder
curl https://pyenv.run | bash
# export the env
echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.bashrc
echo 'command -v pyenv >/dev/null || export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bashrc
echo 'eval "$(pyenv init -)"' >> ~/.bashrc
# Reload the shell
source ~/.bashrc
# install the python required version
pyenv install 3.11.9
# set level
pyenv global 3.11.9

code-server --install-extension mtxr.sqltools-driver-pg
code-server --install-extension mtxr.sqltools
code-server --install-extension cweijan.vscode-database-client2
code-server --install-extension cweijan.vscode-redis-client
