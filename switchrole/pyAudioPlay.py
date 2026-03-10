import subprocess
import sys


def getSoundCardIndex() :
    cardName = "lahainayupikiot"
    try:
        ret = subprocess.run(["cat", "/proc/asound/cards"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        output = ret.stdout
        lines = output.splitlines()
        for line in lines:
            if cardName in line:
                cindex = line.split()[0]
                return cindex
        print(f"card '{cardName}' not found in /proc/asound/cards.")
        return None
    except subprocess.CalledProcessError as e:
        print(f"Command failed with error: {e.stderr}")
        return None

def setSoundMixerCommand(index) :
    commands = [
               ["amixer", "-c", str(index), "cset", "numid=243,iface=MIXER,name='RX HPH Mode'", "CLS_AB"],
               ["amixer", "-c", str(index), "cset", "numid=90,iface=MIXER,name='RX_MACRO RX0 MUX'", "AIF1_PB"],
               ["amixer", "-c", str(index), "cset", "numid=91,iface=MIXER,name='RX_MACRO RX1 MUX'", "AIF1_PB"],
               ["amixer", "-c", str(index), "cset", "numid=6639,iface=MIXER,name='RX_CDC_DMA_RX_0 Channels'", "Two"],
               ["amixer", "-c", str(index), "cset", "numid=112,iface=MIXER,name='RX INT0_1 MIX1 INP0'", "RX0"],
               ["amixer", "-c", str(index), "cset", "numid=115,iface=MIXER,name='RX INT1_1 MIX1 INP0'", "RX1"],
               ["amixer", "-c", str(index), "cset", "numid=107,iface=MIXER,name='RX INT0 DEM MUX'", "CLSH_DSM_OUT"],
               ["amixer", "-c", str(index), "cset", "numid=108,iface=MIXER,name='RX INT1 DEM MUX'", "CLSH_DSM_OUT"],
               ["amixer", "-c", str(index), "cset", "numid=137,iface=MIXER,name='RX_COMP1 Switch'", "1"],
               ["amixer", "-c", str(index), "cset", "numid=138,iface=MIXER,name='RX_COMP2 Switch'", "1"],
               ["amixer", "-c", str(index), "cset", "numid=244,iface=MIXER,name='HPHL_COMP Switch'", "1"],
               ["amixer", "-c", str(index), "cset", "numid=245,iface=MIXER,name='HPHR_COMP Switch'", "1"],
               ["amixer", "-c", str(index), "cset", "numid=269,iface=MIXER,name='HPHL_RDAC Switch'", "1"],
               ["amixer", "-c", str(index), "cset", "numid=270,iface=MIXER,name='HPHR_RDAC Switch'", "1"],
               ["amixer", "-c", str(index), "cset", "numid=520,iface=MIXER,name='RX_CDC_DMA_RX_0 Audio Mixer MultiMedia1'", "1"]
               ]

    for cmd in commands :
        try:
            result = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            print(f"Command {' '.join(cmd)} executed successfully:")
            print(result.stdout)
        except subprocess.CalledProcessError as e:
            print(f"Command {' '.join(cmd)} failed with error:")
            print(e.stderr)

def playAudioFile(card,afile) :
       pcom = ['aplay','-t', 'wav','-r', '48000','-f', 'S16_BE','-c', '2','-D', f'hw:{card},0', afile]
       try:
          result = subprocess.run(pcom, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
          print(f"Command {' '.join(pcom)} executed successfully:")
          print(result.stdout)
       except subprocess.CalledProcessError as e:
          print(f"Command {' '.join(pcom)} failed with error:")
          print(e.stderr)



if __name__ == "__main__" :
    if len(sys.argv) == 2 :
       audioFile = sys.argv[1]
       cardIndex = getSoundCardIndex()
       setSoundMixerCommand(cardIndex)
       playAudioFile(cardIndex,audioFile)
    else :
       print("Please check audio file and file direction !")
