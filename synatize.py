import math
import numpy as np
import pyperclip

if __name__ == '__main__':
   
    with open("./syn_template","r") as template:
        lines = template.readlines()
        
    # translate GLSL to Python
    sin         = math.sin
    cos         = math.cos
    exp         = math.exp
    PI          = np.pi
    step        = lambda a,x : 0 if x < a else 1
    smoothstep  = lambda a,b,x : 0 if x < a else 1 if x > b else 3*((x-a)/(b-a))**2 - 2 * ((x-a)/(b-a))**3
    doubleslope = lambda x,a,d,s: smoothstep(-.00001,a,x) - (1.-s) * smoothstep(0.,d,x-a);
    clamp       = lambda x,a,b: min(b, max(a,x))
    fract       = lambda x: math.modf(x)[0]
    _sin        = lambda x: math.sin(2. * np.pi * (x % 1.))
    _saw        = lambda x: 2.*fract(x) - 1.
    _tri        = lambda x: 4.*abs(fract(x)-.5)-1
    s_atan      = lambda x: 2./np.pi * math.atan(x)
    s_crzy      = lambda x: clamp(s_atan(x) - 0.1*math.cos(0.9*x*math.exp(x)), -1., 1.)
    mix         = lambda x, y, a: a*y + (1-a)*x

    float2str = lambda f: str(int(f)) + '.' if f==int(f) else str(f)[0 if f >= 1 else 1:]
    GLstr       = lambda x: float2str(float(x))

    syncode = ""

    osc_list = []

    for l in lines:
        line = l.split()
        cmd = line[0]
        cid = line[1]
        arg = line[2:]
        print(line)
        
        if cmd == 'def':
            exec(' '.join(line[1:]))
        
        elif cmd == 'float':
            syncode += ' '.join(line[0:3]) + float2str(float(arg[1])) + ';\n';
    
        elif cmd == 'osc':
            print(len(arg))
            osc = {'name':cid, 'shape':arg[0], 'freq':arg[1], 'phase':arg[2] if len(arg)>=2 else '0', 'quant':arg[3] if len(arg)>=3 else '1', \
                   'detune': 0}
            osc_list.append(osc)

        elif cmd == 'detune':
            osc = next((o for o in osc_list if o['name']==cid), None)
            osc['detune'] = float(arg[0])
        
    for osc in osc_list:
        tcode = 't' if osc['quant'] == '1' else '(t*'+GLstr(osc['quant'])+')/'+GLstr(osc['quant'])
        if(osc['detune']>0):
            syncode += 's+= .5*' + osc['shape'] + '(' + osc['freq'] + '*' + tcode + ' + ' + GLstr(osc['phase']) + ')' \
                      + ' + .5*' + osc['shape'] + '(' + osc['freq'] + '*' + float2str(1-osc['detune']) + '*' + tcode + ' + ' + GLstr(osc['phase']) + ');'
        else:
            syncode += 's+= ' + osc['shape'] + '(' + osc['freq'] + '*' + tcode + ' + ' + GLstr(osc['phase']) + ');'

    #syncode = syncode.replace(' =','=').replace('= ','=').replace('\n','')
    
    print("")
    print("AND NOW THE CODE IS:")
    print(syncode)

    gf = open("syn_framework")
    glslcode = gf.read()
    gf.close()
    
    BPM = 80
    note = 25

    glslcode = glslcode.replace("//SYNCODE",syncode) \
                       .replace("const float note = 24.;", "const float note = " + float2str(note) + ";") \
                       .replace("const float BPM = 80.;", "const float BPM = " + float2str(BPM) + ";")

    pyperclip.copy(glslcode)
    print("", "full shader written to clipboard")
