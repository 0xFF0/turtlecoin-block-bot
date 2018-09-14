import discord #python3 -m pip install -U https://github.com/Rapptz/discord.py/archive/rewrite.zip#egg=discord.py
import asyncio
import turtlecoin
import json
import sys
import time
import random
import hexdump
import http
import logging
from collections import deque

ENABLE_DEBUG_LOG = False


if ENABLE_DEBUG_LOG:
	logging.basicConfig(
		filename="bbot.log",  
		level=logging.DEBUG,
		format="%(asctime)s:%(levelname)s:%(message)s"
		)
else:
	logging.disable(logging.CRITICAL)
	
# discord stuff
client = None
tc = None
tclbh = None
token = None
csuccess = None

try:
	token = open('tokenfile').read()
except:
	pass


logging.debug("Starting turtlecoin-block-stat")

if token and token != 'YOUR-TOKEN-HERE':
	try:
		client = discord.Client()
	except:
		print("Couldn't connect to discord client")
else:
	print("Please configure your Discord token")


def connect_to_turtlecoind(atno = 2):
	global tc
	global tclbh
	global csuccess
	
	try:
		logging.debug("[TURTLECOIN] Connection to public.turtlenode.io")
		tc = turtlecoin.TurtleCoind(host='public.turtlenode.io', port=11898)
		
		logging.debug("[TURTLECOIN]Requesting get_last_block_header()")
		tclbh = tc.get_last_block_header()['result']
		
		logging.debug("[TURTLECOIN] Requesting get_last_block_header() - Success")
		logging.debug(tclbh)
		csuccess = True
	except (ValueError, ConnectionError) as e:
		logging.error(e)
		print(f"Couldn't connect. Attempt {atno} to connect")
		atno += 1
		time.sleep(5)
		connect_to_turtlecoind(atno)

	else:
		print("Connected, moving on")




def decode_tx_extra(tx_extra_hex):
	"""Returns a list of string data decoded from the Transaction Extra Field
	See https://cryptonote.org/cns/cns005.txt for proper formatting of tx_extra_hex
	"""
	curr_index = 0
	custom_data_arr = []
	payment_id = None
	tx_extra_decoded = []  # decoded data will be a list of strings, to be formatted later

	logging.debug("[TURTLECOIN] decode_tx_extra()")
	if not isinstance(tx_extra_hex, str):
		raise TypeError(f'decode_tx_extra() expects 1 argument of type string, but received {tx_extra_hex}')

	while(curr_index < len(tx_extra_hex)):
		# Each subfield must begin with a tag 00, 01, or 02
		if tx_extra_hex.startswith('00', curr_index):  # padding
			# All zeroes from here. No need to report this. We're done!
			curr_index = len(tx_extra_hex)
		elif tx_extra_hex.startswith('01', curr_index):  # payment ID
			curr_index += 2
			transactionPubKey = tx_extra_hex[curr_index:curr_index + 64]
			curr_index += 64
		elif tx_extra_hex.startswith('02', curr_index):  # extra nonce (custom data)
			# next byte will specify size
			curr_index += 2
			subfield_size = 2 * int(tx_extra_hex[curr_index:curr_index + 2], 16)
			curr_index += 2
			data = tx_extra_hex[curr_index:curr_index + subfield_size]
			curr_index += subfield_size
			custom_data_arr.append(data)
			curr_index += subfield_size
		else:
			tx_extra_decoded.append(f"Hm, something went wrong. I got an invalid subfield tag of {tx_extra_hex[curr_index:curr_index + 2]}")
			curr_index += 2

	if transactionPubKey:
		tx_extra_decoded.append(f"Transaction public key: {transactionPubKey}")

	for hash in custom_data_arr:
		hexView = hexdump.hexdump((bytes.fromhex(hash)), result='return')
		hexView = "".join("        " + x +"\n" for x in hexView.split("\n"))
		tx_extra_decoded.append(f"Custom Data (hexview): \n{hexView}")

	return tx_extra_decoded

success = None

def getstats(height):
	global success
	logging.debug("[TURTLECOIN] getstats() -> " + str(height))
	try:
		tcgl = tc.get_last_block_header()['result']['block_header']

		# height of the latest block
		height = tcgl['height']
		# hash of latest block
		hash = tcgl['hash']
		# whether atest block is orphan or not
		orphan = tcgl['orphan_status']

		# reward of the latest block
		reward = tcgl['reward']
		breward = reward / 100

		# wheter the time the block took to make is acceptable or not
		timex = tcgl['timestamp']
		prevhash = tcgl['prev_hash']
		glb = tc.get_block(prevhash)
		time2 = glb['result']['block']['timestamp']
		timed = timex - time2
		rock = "388916188715155467"
		pingrock = "<@" + rock + ">"
		blocktime = ""
		if timed <= 4:
			blocktime += f"Block was too fast, {timed} seconds"
			pingrock += ""
		elif timed >= 90:
			blocktime += f'Took too long, {timed} seconds.'
			pingrock += ""
		else:
			blocktime += f"Took {timed} seconds to make, pretty nice"
			pingrock = ""

		# size of the block
		txs = tc.get_block(hash)  # changed 2 vars to one var, keeping name.
		bsizes = txs['result']['block']['blockSize']

		# number of transaction hashes in the block
		ntxs = len(txs['result']['block']['transactions'])

		# each tx hash in the block
		hashes = [x['hash'] for x in txs['result']['block']['transactions']]

		# size of each tx
		hahsizes = [z['size'] for z in txs['result']['block']['transactions']]

		# size of all the txs
		txsize = txs['result']['block']
		txsizes = txsize['transactionsCumulativeSize']

		teta = []
		deteta = []
		paymentId = []

		for txhash in hashes:
			# get tx
			transaction = tc.get_transaction(txhash)['result']
			# tx extra hash
			extra = transaction['tx']['extra']
			teta.append(extra)
			# Decoded version of tx_extra:
			deteta.append(decode_tx_extra(extra))
			paymentId.append(transaction['txDetails']['paymentId'])

		# size of tx extra
		txes = bsizes - txsizes

		# % of txs in the block
		txp = txsizes / bsizes * 100

		# % of tx_extra in the block
		txep = txes / bsizes * 100

		success = True
		
		return {'height': height, 'hash': hash, 'orphan': orphan, 'reward': breward, \
		'bsizes': bsizes, 'blocktime': blocktime, 'ntxs': ntxs, 'hashes': hashes, 'hahsizes': hahsizes, \
		'txsizes': txsizes, 'teta': teta, 'deteta': deteta, 'txes': txes, 'txp': txp, 'txep': txep, 'pingrock': pingrock, 'paymentId':paymentId}

		
	
	except (ValueError, ConnectionError, http.client.HTTPException) as e:
		logging.error(e)
		print("GetStat Error")
		success = False

def prettyPrintStats(blockstats):
	if success:
		msg = "WE FOUND A NEW BLOCK!\n"
		msg += "\nHeight: {} \n".format(blockstats['height'])
		msg += "Hash: {} \n".format(blockstats['hash'])
		msg += "Orphan: {} \n".format(blockstats['orphan'])
		msg += "Reward: {} \n".format(blockstats['reward'])
		msg += "Size: {} \n".format(blockstats['bsizes'])
		msg += "Time took to make: {} \n".format(blockstats['blocktime'])

		msg += "\nNo. of txs in the block: {}".format(blockstats['ntxs'])
		msg += "\nTotal size of the txs: {}".format(blockstats['txsizes'])
		msg += "\nTotal size of tx_extra(s): {}".format(blockstats['txes'])
		for idx, hash in enumerate(blockstats['hashes']):
			msg += f"\n\nTx {idx} (size {blockstats['hahsizes'][idx]}):"
			msg += f"\n    Hash: {hash}"
			if len(blockstats['paymentId'][idx])>0:
				msg += f"\n    Payment Id: {blockstats['paymentId'][idx]}"
			msg += f"\n    tx_extra: {blockstats['teta'][idx]}"
			if idx < len(blockstats['deteta']):
				for line in blockstats['deteta'][idx]:
					msg += f"\n    {line}"

		msg += "\n\nPercentage of txs in the block: {} %".format(blockstats['txp'])
		msg += "\nPercentage of tx_extra in the block: {} % ".format(blockstats['txep'])

		# msg += blockstats['pingrock']

	else:
		msg = "Error occured, could not retrieve stats"

	print(msg)

	return msg


class client_check(object):
	def __init__(self, client):
		self.client = client

	def __call__(self, func):
		if not self.client:
			print("Cannot connect to Discord without a valid token. Bot will attempt to print to console.")
			# Return the function unchanged, not decorated with Discord API.
			return func
		return self.client.event(func)


@client_check(client)
async def on_ready():
	print("connected")
	height = tclbh['block_header']['height']
	if client:
		channel = client.get_channel(459931714471460864)
	global displayHeight 
	displayHeight = deque(['0','0','0','0','0','0','0','0','0','0','0','0','0','0','0']) #this avoid display twice the same block on discord
	while True:
		bsuccess = None
		try:
			nheight = tc.get_block_count()['result']['count']
			bsuccess == True
			if height != nheight and nheight not in displayHeight:
				print("val changed")
				print(nheight)
				print(height)
				height = nheight
				print(height)
				displayHeight.append(nheight)
				displayHeight.popleft()
				if client:
					discordMsg =prettyPrintStats(getstats(nheight))
					[await channel.send("```\n" + discordMsg[i: i + 1990] + "```") for i in range(0, len(discordMsg), 1990)]

				else:
					prettyPrintStats(getstats(nheight))
	
			await asyncio.sleep(0.5)
		except Exception as e:
			logging.error(str(e.__class__) + "  -  " + str(e))
			print("get_block_count() error : " + str(e.__class__))
			await asyncio.sleep(1)


def start_local_event_loop():
	print("*** Starting local event loop with TurtleCoind ***")
	loop = asyncio.get_event_loop()
	loop.run_until_complete(on_ready())
	loop.close()


if __name__ == '__main__':
	connect_to_turtlecoind()

	if client:
		client.run(token)
	else:
		try:
			start_local_event_loop()
		except KeyboardInterrupt as err:
			print("\nShutdown requested. Exiting...")
			sys.exit(0)
