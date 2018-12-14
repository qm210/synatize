import math
import numpy as np
import pyperclip
import re

GLfloat = lambda f: str(int(f)) + '.' if f==int(f) else str(f)[0 if f >= 1 else 1:]

def GLstr(s):
    try:
        f = float(s)
    except ValueError:
        return s
    else:
        return GLfloat(f)

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
       
        print(line)

        if cmd == 'main':
            if form_main is not None: print("WARNING: multiple main forms. Last definition will be the one.")
            form_main = {'ID':'main', 'type':'main', 'amount':len(line)-1, 'terms':line[1:]}

        elif cmd == 'const':
            form_list.append({'ID':cid, 'type':cmd, 'value':float(arg[0])})
    
        elif cmd == 'osc' or cmd == 'lfo':
            form_list.append({'ID':cid, 'type':cmd, 'shape':arg[0], 'freq':arg[1], 'phase':arg[2] if len(arg)>2 else '0', 'par':arg[3] if len(arg)>3 else '0'})

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
        print(form['ID'])
        
        
    if not form_main:
        print("WARNING: no main form defined! will return empty sound")
        syncode = "s = 0.; //some annoying weirdo forgot to define the main form!"

    else:
        syncode = "s = "
        for term in form_main['terms']:
            syncode += instance(term) + '\n' + 6*' ' + '+ ' if term != form_main['terms'][-1] else ';'

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

def instance(ID, mod={}):

    form = next((f for f in form_list if f['ID']==ID), None)
    
    if mod: form.update(mod)
    
    if '*' in ID:    
        IDproduct = ID.split('*')
        product = ''
        for factorID in IDproduct:
            product += instance(factorID) + ('*' if factorID != IDproduct[-1] else '')
        return product;

#    if '

    elif not form:
        return GLstr(ID)
    
    elif form['type']=='uniform':
        return ID
    
    elif form['type']=='const':
        return GLfloat(form['value'])
    
    elif form['type']=='form':
        if form['OP'] == 'detune':
            return 's_atan(' + instance(form['source']) + '+' + instance(form['source'],{'freq':'(1.-' + instance(form['amount']) + ')*'+param(form['source'],'freq')}) + ')'
        else:
            return '1.'

    elif form['type']=='osc':
            if form['shape'] == 'sin':
                if(float(form['phase'])==0):
                    return 'vel*_sin(' + instance(form['freq']) + '*t)'
                else:
                    return 'vel*_sin(' + instance(form['freq']) + '*t,' + instance(form['phase']) + ')'
            elif form['shape'] == 'saw':
                return 'vel*(2.*fract(' + instance(form['freq']) + '*t+' + instance(form['phase']) + ')-1.)';
            else:
                return '0.'
                
    elif form['type']=='lfo':
        pass

    elif form['type']=='env':
        pass

    else:
        return '1.';

def param(ID, key):
    form = next((f for f in form_list if f['ID']==ID), None)
    try:
        value = form[key]
    except KeyError:
        return ''
    except TypeError:
        return ''
    else:
        return value

if __name__ == '__main__':
    main()
