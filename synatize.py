import math
import numpy as np
import pyperclip

GLfloat = lambda f: str(int(f)) + '.' if f==int(f) else str(f)[0 if f >= 1 else 1:]
GLstr = lambda x: GLfloat(float(x))

synhead = ""
syncode = ""

#reserved keywords you cannot name a form after
_f = {'ID':'f', 'type':'uniform'}
_t = {'ID':'t', 'type':'uniform'}
_B = {'ID':'B', 'type':'uniform'}
_vel = {'ID':'vel', 'type':'uniform'} # maybe we want to use that
form_list = [_f, _t, _B, _vel]

form_main = None

def main():

    global synhead
    global syncode
    global form_list
    global form_main
   
    with open("./syn_template","r") as template:
        lines = template.readlines()
        
    for l in lines:
        line = l.split()
        cmd = line[0]
        cid = line[1]
        arg = line[2:]
       
        print(cmd, len(arg))

        if cmd == 'main':
            if form_main is not None: print("WARNING: multiple main forms. Last definition will be the one.")
            form_main = {'ID':'main', 'type':'main', 'amount':len(line)-1, 'terms':line[1:]}

        elif cmd == 'const':
            form_list.append({'ID':cid, 'type':cmd, 'value':float(arg[0])})
    
        elif cmd == 'osc' or cmd == 'lfo':
            form_list.append({'ID':cid, 'type':cmd, 'shape':arg[0], 'freq':arg[1], 'phase':arg[2] if len(arg)>2 else '0'})

        elif cmd == 'env': #env NAME adsf a d s f
            form_list.append({'ID':cid, 'type':cmd, 'shape':arg[0], 'attack':arg[1], 'decay':arg[2], 'sustain':arg[3], 'release':arg[4]})

        # global automation curve - no idea on how to parametrize, but have that idea in mind
        elif cmd == 'gac':
            pass
            form_list.append(form_main)

        # advanced forms ("operators"), like detune, chorus, delay, waveshaper/distortion, and more advanced: filter, reverb
        elif cmd == 'form':
            op = arg[0]
            form = {'ID':cid, 'type':cmd, 'OP':op}

            if op == 'mix':
                form.update({'amount':len(arg), 'terms':arg[1:]})
            
            elif op == 'detune':
                form.update({'source':arg[1], 'amount':arg[2]})
            
            else:
                pass
                
            form_list.append(form)


    print("\nLIST OF FORMS:\n", sep="")
    for form in form_list:

        if form['type'] == 'const':
            synhead += 'float ' + form['ID'] + ' = ' + GLfloat(form['value']) + ';\n'

        elif form['type'] == 'osc':
            synhead += 'float ' + form['ID'] + '(float t, float f, float B, float vel, float phase, float par){return ';
            
            if form['shape'] == 'sin':
                synhead += 'vel * sin(2. * PI * mod(f*t,1.) + phase);}\n'
            else:
                synhead += '0.;}\n'
    
    print("\nBUILD SYN HEADER:\n", synhead, sep="")

    if not form_main:
        print("WARNING: no main form defined! will return empty sound")
        syncode = "s = 0.; //some annoying weirdo forgot to define the main form!"

    else:
        syncode = "s = "
        for term in form_main['terms']:
            termfac = term.split('*')
            for fac in termfac:
                syncode += instance(fac) + ('*' if fac != termfac[-1] else '')
            syncode += '\n' + 6*' ' + '+ ' if term != form_main['terms'][-1] else ';'

    gf = open("syn_framework")
    glslcode = gf.read()
    gf.close()

    print("\nBUILD SYN BODY:\n", syncode, sep="")
    
    BPM = 80
    note = 24

    glslcode = glslcode.replace("//SYNCODE",syncode) \
                       .replace("const float note = 24.;", "const float note = " + GLfloat(note) + ";") \
                       .replace("const float BPM = 80.;", "const float BPM = " + GLfloat(BPM) + ";")

    pyperclip.copy(glslcode)
    print("\nfull shader written to clipboard")

def instance(ID):
    global form_list
    form = next((f for f in form_list if f['ID']==ID), None)
    
    if not form:
        return GLstr(ID)
    
    elif form['type']=='uniform':
        return ID
    
    elif form['type']=='const':
        return GLfloat(form['value'])
    
    elif form['type']=='form':
        print(form)
        
        if form['OP'] == 'detune':
            return 's_atan(' + instance(form['source']) + '+(1-' + instance(form['amount']) + ')*' + instance(form['source']) + ')'
        else:
            return '1.'
        
    else: #basic forms - but you have to differentiate
        return ID + '(t,f,B)'

if __name__ == '__main__':
    main()
