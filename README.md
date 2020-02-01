# abode

abode is a self-hosted home server which aggregates your discord data in a discoverable format.

## status

abode is in early personal testing but I've already found it invaluable for easily querying things. The motivated individual could figure out how to properly run a version locally (tl;dr: postgres database, config with postgres dsn and token, run one client and one api), but I'm not currently planning to extensively document the process (you should understand it to use it).

## ok but why

Discord in general is only relatively friendly to data export as evident from the [Discord Data Package](https://support.discordapp.com/hc/en-us/articles/360004957991-Your-Discord-Data-Package), which lacks messages not sent by you, attachments, and various other relevant data (take it from me, I built the original system while there). The data package also serves as a poor real time solution due to its multi-week delay in between requesting packages, and the long generation time of each individual package. abode fills in for this lack of flexibility and features on Discords side by tracking, storing and indexing your data. abode was designed to be used by individuals for tracking only data that "belongs" (any data discord makes visible to the end user) to them, and thus won't work for large-scale or wide berth data-mining.

The explanation is all well and good, but it doesn't really explain why you would even _want_ your data archived locally. While different folks can have different reasons, the primary advantages to running abode come from:

- data backup (for when sinister deletes all the channels again)
- fast and powerful querying (for finding **anything** quickly and easily)
- audit log (for when things happened more than 90 days ago)
- data insights (for understanding how you use and experience discord)

## how

abode includes a client component which connects to discord on behalf of your user (with your token, so this is considered ["self botting"](https://support.discordapp.com/hc/en-us/articles/115002192352-Automated-user-accounts-self-bots-) by discord, and could get your account banned), an api server which can process queries written in a custom-DSL, and a lightweight frontend for querying. abodes primary use is for power-user level querying of its internal data archive, but it can also be used as a generic data API for other applications.

## query language

abode is built around a custom search query language, which is intentionally simple but can be quite powerful when used correctly. The real power of abodes queries comes directly from postgres, where abode leans on full text search and unique indexes to keep query response time fast.

| Syntax | Meaning |
|--------|---------|
| field:value | fuzzy match of value |
| field:"value" | case insensitive exact match of value |
| field="value" | case sensitive exact match of value |
| field:(x y) | fuzzy match of x or y |
| field:x AND NOT field:y | fuzzy match of x and not y |
| (field:a AND field:b) OR (field:c AND field:d) | fuzzy match of a and b or c and d |
| -> x y z | select fields x, y, and z |

## screenshots

![](https://i.imgur.com/LIFBQAR.png)
![](https://i.imgur.com/eFFvES0.png)
![](https://i.imgur.com/p0fNmWG.png)