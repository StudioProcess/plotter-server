import re

def to_num(str):
    num = float(str)
    if num.is_integer(): return int(num)
    return num

# E.g.: 'M 12.012 2.0 30'
def decode_command(str):
    str = str.strip()
    # check whole string
    check = re.fullmatch(r'[ML](\s+\d+\.?\d*\s*)+', str);
    if not check: return None
    type = re.match(r'^[ML]', str)[0]
    nums = re.findall(r'\d+\.?\d*', str)
    nums = list(map(to_num, nums))
    return (type, nums)

# E.g.: 'M 12.012 2.0 L 10 30 23.4 99.0 M 10.0 22'
def decode_path(str):
    check = re.fullmatch(r'([ML](\s+\d+\.?\d*\s*)+)+', str);
    if not check: return None
    cmds = re.split(r'\s+(?=[ML])', str)
    cmds = map(decode_command, cmds)
    cmds = list(filter(lambda x: x != None, cmds))
    if not cmds: return None
    return cmds

if __name__ == '__main__':
    # x = decode_command('M 12.012 2.0 30');
    # x = decode_command('M 1.2');
    # print(x)
    
    x = decode_path('M 12.012 2.0 L 10 30 23.4 99.0 M 10.0 22');
    # x = decode_command('M 1.2');
    print(x)
