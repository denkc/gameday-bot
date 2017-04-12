Gameday Bot
================================
Post highlights from your favorite baseball team's game today to Slack

Configure
=============

Set up config.py
- copy Slack API token from https://api.slack.com/custom-integrations/legacy-tokens
- change team code if desired

```
cp gameday/config.py.template gameday/config.py
vim gameday/config.py
```

Setup
=============

```
virtualenv env --no-site-packages
source env/bin/activate
python setup.py install
```

Run
=============

Currently set up to be run as a cron

```
env/bin/gameday
```