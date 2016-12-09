import boto3
import json
import logging
import os

from base64 import b64decode
from urlparse import parse_qs
from riotwatcher import RiotWatcher
import time
import collections
from math import ceil


ENCRYPTED_EXPECTED_TOKEN = os.environ['kmsEncryptedToken']

ENCRYPTED_EXPECTED_API = os.environ['riotEncryptedApi']

kms = boto3.client('kms')
expected_token = kms.decrypt(CiphertextBlob=b64decode(ENCRYPTED_EXPECTED_TOKEN))['Plaintext']

api = RiotWatcher(ENCRYPTED_EXPECTED_API)

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def respond(err, res=None):
    return {
        'statusCode': '400' if err else '200',
        'body': err.message if err else json.dumps(res),
        'headers': {
            'Content-Type': 'application/json',
        },
    }


def lambda_handler(event, context):
    params = parse_qs(event['body'])
    print(params['token'])
    token = params['token'][0]
    if token != expected_token:
        logger.error("Request token (%s) does not match expected", token)
        return respond(Exception('Invalid request token'))

    user = params['user_name'][0]
    command = params['command'][0]
    channel = params['channel_name'][0]
    command_text = params['text'][0]
    if command_text == "help":
        return respond(None, "here is a list of what you can do: \n1. op.gg: will print out a link to your op.gg page. Pass in summoner name.\n2. lastGame: will get information for the last game you played. Make sure you also pass in your summoner name\n3. featuredGames: prints out some of the featured games\n4. id: will return your summoner id\n5. help:Will output a basic help page\n")

    command_split = command_text.split(' ', 1)
    size = len(command_split)
    command = ""
    summoner1 = ""
    id1 = ""
    id2 = ""
    if size > 1:
        command = command_split[0]
        summoner1 = api.get_summoner(name=command_split[1])
        id1 = summoner1['id']
    if not summoner1:
        return respond(None, "we failed")
    if command == "op.gg":
        op = "http://na.op.gg/summoner/userName=" + command_split[1]
        return respond(None, "here is your op.gg link: %s" % (op))
    if command == "lastGame":
        recent_games = api.get_recent_games(id1)
        firstGame = recent_games['games'][0]['gameId']
        stats, matchUrl = getStats(api, id1, firstGame)
        return respond(None, "Here are your stats: {kills: %s, deaths: %s, winner: %s, KDA: %s, assists: %s, champLevel: %s, matchUrl: %s" % (stats["kills"], stats["deaths"], stats["winner"], stats["KDA"], stats["assists"], stats["champLevel"], matchUrl))
    if command == "featuredGames":
        player = api.get_featured_games()['gameList'][0]['participants'][0]['summonerName']
        return response(None, "Here is the featured Summoner: %s" % (player))
    if command == "id":
        return response(None, "The id belonging to %s is %s" % (command_split[1], id1))

def getStats(RiotWatcher, id1, firstGame):
    #timeOut(api)

    summoners = []
    summNames = []
    participants = []
    stats = {}
    match = api.get_match(firstGame)
    participantIdentities = match['participantIdentities']
    for p in participantIdentities:
    	player = p['player']
    	summonerIds = player['summonerId']
    	summoners.append(summonerIds)
    	if id1 in summoners:
    		participantId = p['participantId']
    		participants.append(participantId)
    		summonerName = player['summonerName']
    		matchUrl = player['matchHistoryUri']
    		summNames.append(summonerName)


    participantStats = match['participants']
    for par in participantStats:
    	if participants[0] == par['participantId']:

    		champId = par['championId']
    		kills = par['stats']['kills']
    		deaths = par['stats']['deaths']
    		assists = par['stats']['assists']
    		championLevel = par['stats']['champLevel']
    		winner = par['stats']['winner']
    		key = 'stats'
    	#stats.setdefault('stats', {})
    		stats['kills'] = kills
    		stats['deaths'] = deaths
    		stats['assists'] = assists
    		stats['winner'] = winner
    		stats['champLevel'] = championLevel
    		kda = (kills + assists) / float(deaths)
    		kda = ceil(kda * 100) / 100.0
    		stats['KDA'] = kda

    		return stats, matchUrl
