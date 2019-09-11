'''
Bot for monitoring a Discord Channel. Bot monitors the discord for online users and monitors user
game presence. Sends LED light statuses based on game presence to an available feed at adafruit.io as a single byte for NodeMCU endpoint
notifiers or other IoT devices to read and react.
'''

import discord
from discord.ext import commands
from Adafruit_IO import Client, Feed, Data, RequestError
from enum import Enum


ADAFRUIT_IO_KEY = "ADAFRUIT_IO_KEY"
ADAFRUIT_IO_USERNAME = "ADAFRUIT_IO_USERNAME"
ADAFRUIT_IO_VIDISCORDMONITOR_FEED_KEY = 'ADAFRUIT_IO_VIDISCORDMONITOR_FEED_KEY'

DISCORDBOT_PRIVATE_KEY = 'DiscordBotPrivateKeyHere'

# Create an instance of the REST client.
aio = Client(ADAFRUIT_IO_USERNAME, ADAFRUIT_IO_KEY)

#Try and open feed, if nonexistent, create:
try:
    viDiscordMonitorFeed = aio.feeds(ADAFRUIT_IO_VIDISCORDMONITOR_FEED_KEY)
except RequestError:
    print('Error accessing Adafruit io')

'''
LightByte: a special variable containing all data needed for which colors an RGB light should be flashing in a single 
byte (integer) by combining Binary with "Red Orange Yellow Green Blue Indigo Violet Off" (ROYGBIV+White). This variable is 
initialized to 0 representing "No Lights." This is done so that only a single variable needs to be stored, and only
a single variable needs to be read to determine which status lights need to flash.

LightByte key:
255 = All Statuses + White
128 = All (Flash Red, Orange, Yellow, Green, Blue, Indigo, and Violet.)
64 =  Flash Orange, Yellow, Green, Blue, Indigo, and Violet
and so on.

This will likely need to be interpreted via modulo on the other end by whatever devices are using the LightByte
variable. On this LightByte simply needs to += whatever LED wished to be flashed.
'''

AssembleLightOn = False

class LightByteLED(Enum):
    RED = 128
    ORANGE = 64
    YELLOW = 32
    GREEN = 16 #Two or more players playing the same game
    BLUE = 8 #One or more players playing starcraft
    INDIGO = 4
    VIOLET = 2
    WHITE = 1

description = '''viDiscordMonitorBot'''
bot = commands.Bot(command_prefix='/', description=description)

@bot.event
async def on_ready():
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print('------')
    checklightstatuses()

@bot.event
async def on_member_update(before, after):
    checklightstatuses()

@bot.command()
async def whoson(ctx):
    """Gets a list of online users."""
    members = bot.get_all_members()
    membersstring = ''
    for member in members:
        if(member.status != discord.Status.online):
            membersstring += str(member) + '\n'
    await ctx.send(membersstring)

@bot.command()
async def whatsplaying(ctx):
    """Gets a list of all games being played."""
    members = bot.get_all_members()
    memgamesstring = ''
    for member in members:
        '''Checks if members activity has value a game and not equal to nothing. 
        Needs to be done as it can screw up command. '''
        if(member.activity != None and member.activity.type == discord.ActivityType.playing):
            memgamesstring += str(member.activity.name) + '\n'
    await ctx.send(memgamesstring)

@bot.command()
async def assemble(ctx):
    global AssembleLightOn
    if(AssembleLightOn == True):
        AssembleLightOn = False
        LightStatusString = "Off"
    else:
        AssembleLightOn = True
        LightStatusString = "On"

    checklightstatuses()
    await ctx.send("Assemble Light is " + LightStatusString)


#Check things to see if light statuses should be lit and post in binary format to Adafruit.io feed
def checklightstatuses():
    global AssembleLightOn

    LightByte = 0
    print('Member Update')
    print('Checking Num Played Games:')
    #If two or more players are playing the same game
    if(getListNumberOfDuplicates(getGamesPlayingList()) > 0):
        print('Two or more players are playing the same game.')
        LightByte += LightByteLED.GREEN.value

    if(checkNumGamesPlaying() >= 3):
        print('Atleast three players on the server are playing a game.')
        LightByte += LightByteLED.RED.value

    for Game in getGamesPlayingList():
        if str(Game) == 'Call of Duty: Modern Warfare 2':
            print('Someone is playing Modern Warfare 2')
            LightByte += LightByteLED.YELLOW.value

    for Game in getGamesPlayingList():
        if str(Game) == 'StarCraft II':
            print('Someone is playing StarCraft II')
            LightByte += LightByteLED.BLUE.value

    if(AssembleLightOn):
        LightByte += 1 #Toggle white light if assemble light on.

    #Convert LightByte to byte:
    LightByte = '{0:08b}'.format(LightByte)

    #Post to Adafruit IO
    print('LightByte posting at value: ', str(LightByte))
    postToAdafruitIO(LightByte)



#Gets a list of all games being played on the server:
def getGamesPlayingList():
    GamesPlaying = ['']
    members = bot.get_all_members()
    for member in members:
        '''Checks if members activity has value a game and not equal to nothing. 
        Needs to be done as it can screw up command. '''
        if (member.activity != None and member.activity.type == discord.ActivityType.playing):
            GamesPlaying.append(str(member.activity.name))

    return GamesPlaying

def checkListHasDuplicates(mylist):
    #Check for duplicates by removing duplicates from one list using "set()" and comparing list length.
    if(len(mylist) != len(set(mylist))):
        return True
    else:
        return False

def getListNumberOfDuplicates(mylist):
    return len(mylist) - len(set(mylist))

def postToAdafruitIO(myLightByte):
    aio.send(ADAFRUIT_IO_VIDISCORDMONITOR_FEED_KEY, myLightByte)

#Get number of games being played by people on server:
def checkNumGamesPlaying():
    NumGamesPlaying = len(getGamesPlayingList())
    print('Number of games being played on server: ', str(NumGamesPlaying))
    return NumGamesPlaying

#Begin bot.
bot.run(DISCORDBOT_PRIVATE_KEY)

