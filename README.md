Red Packet Activity Telegram Bot using Python-Telegram-Bot
Features:

Set Red Packet Parameters

Group administrators can set red packet parameters using the /setrp command.
Parameters include: total amount, number of packets, and optional password.
Format: /setrp <total_amount> <number_of_packets> [<password>]
Successfully setting parameters will immediately publish the red packet activity in the group.
Red packet display format: image containing red packet information and a "Grab Red Packet" button.
Grabbing Red Packets

No password: Group members can click the button to participate in the red packet activity.
With password: Group members enter the password to participate in the red packet activity.
The bot randomly allocates the red packet amount and replies with the amount grabbed.
The total amount grabbed by users must equal the set amount.
Red Packet Results

When a user grabs a red packet, the bot publishes updated red packet information.
Information includes: balance, number grabbed/remaining, and information of users who grabbed (username/amount/time).
When all red packets are grabbed, the activity ends.
The bot sends a file to the group administrator containing information of users who grabbed the red packets.
