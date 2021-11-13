from subprocess import run

def find_firefox():
    paths = run(['mdfind', 'kMDItemFSName == Firefox.app'], capture_output=True).stdout.splitlines()
    assert len(paths) > 0
    return paths[0].strip().decode() + '/Contents/MacOS/firefox'

if __name__ == '__main__':
    print(find_firefox())
