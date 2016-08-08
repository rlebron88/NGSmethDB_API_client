#!/usr/bin/env python3

'''
NGSmethDB website: http://bioinfo2.ugr.es:8080/NGSmethDB/
'''

def percentile(N, percent, key=lambda x:x):
    if not N:
        return None
    k = (len(N)-1) * percent
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return key(N[int(k)])
    d0 = key(N[int(f)]) * (c-k)
    d1 = key(N[int(c)]) * (k-f)
    return d0+d1

def welcome(display):
    text = '''
    <b>Welcome to NGSmethAPI Client!</b>

    NGSmethAPI Client allows you to download data from the NGSmethDB programmatically.
    You only need to select an assembly, samples of interest and BED file with genomic regions to consult.

    Now you must select an assembly and samples of interest.
    If you save the configuration file, you can use it to query data without the program ask you anything.
    '''
    if display:
        try:
            PyZenity.InfoMessage(text, title = title)
        except:
            logger.warning('Unable to use Zenity! Dialog will be used instead.')
            display = False
            main(args)
    else:
        d = dialog.Dialog(dialog = 'dialog' if not OS.startswith('win') else os.path.join(os.path.dirname(os.path.realpath(__file__)), 'windows', 'dialog.exe'), autowidgetsize = True)
        d.set_background_title("NSGmethDB API Client")
        d.msgbox(text.replace('<b>','\Zb').replace('</b>','\ZB'), title = title, colors = True)

def get_assembly(server):
    url = os.path.join(server, 'info')
    n = 0
    while True:
        try:
            res = requests.get(url)
            break
        except:
            n += 1
            if n < retries:
                logger.warning('Internet connection failed. Retrying...')
            else:
                logger.critical('Unable to connect to the Internet! Leaving the program...')
                raise SystemExit
    if res.status_code != 200:
        logger.error('API Error: ' + str(res.status_code))
        logger.critical('Unable to reach the NGSmethDB API Server! Leaving the program...')
        raise SystemExit
    data = res.json()
    text = "Select an assembly from the list below."
    if display:
        names = ['Select', 'Assembly', 'Common', 'Species']
        choices = [('', a['assembly'], a['common'], a['species']) for a in data]
        assembly = PyZenity.List(names, title = title, text = text, boolstyle = "radiolist", data = choices)[0]
        if not assembly:
            logger.critical('Assembly not selected. Leaving the program...')
            raise SystemExit
        return assembly
    else:
        d = dialog.Dialog(dialog = 'dialog' if not OS.startswith('win') else os.path.join(os.path.dirname(os.path.realpath(__file__)), 'windows', 'dialog.exe'), autowidgetsize = True)
        d.set_background_title("NSGmethDB API Client")
        choices = [(a['assembly'], " ".join([a['common'], '(' + a['species'] + ')']), False) for a in data]
        code, assembly = d.radiolist(text, title = title, choices = choices)
        if code != d.OK or not assembly:
            logger.critical('Assembly not selected. Leaving the program...')
            raise SystemExit
        else:
            return assembly

def get_samples(assembly, server):
    url = os.path.join(server, assembly, 'info')
    n = 0
    while True:
        try:
            res = requests.get(url)
            break
        except:
            n += 1
            if n < retries:
                logger.warning('Internet connection failed. Retrying...')
            else:
                logger.critical('Unable to connect to the Internet! Leaving the program...')
                raise SystemExit
    if res.status_code != 200:
        logger.error('API Error: ' + str(res.status_code))
        logger.critical('Unable to reach the NGSmethDB API Server! Leaving the program...')
        raise SystemExit
    data = res.json()
    text = "Select one or more samples from the list below."
    if display:
        names = ['Select', 'ID', 'Individual', 'Sample']
        choices = []
        for individual in sorted(data.keys()):
            for sample in sorted(data[individual]):
                choices.append(('', ".".join([individual, sample]), individual, sample))
        samples = PyZenity.List(names, title = title, text = text, boolstyle = "checklist", data = choices)
        if not samples[0]:
            logger.critical('Sample(s) not selected. Leaving the program...')
            raise SystemExit
        return samples
    else:
        d = dialog.Dialog(dialog = 'dialog' if not OS.startswith('win') else os.path.join(os.path.dirname(os.path.realpath(__file__)), 'windows', 'dialog.exe'), autowidgetsize = True)
        d.set_background_title("NSGmethDB API Client")
        choices = []
        for individual in sorted(data.keys()):
            for sample in sorted(data[individual]):
                choices.append((".".join([individual, sample]), " ".join([individual, sample]), False))
        code, samples = d.checklist(text, title = title, choices = choices)
        if code != d.OK or not samples:
            logger.critical('Sample(s) not selected. Leaving the program...')
            raise SystemExit
        else:
            return samples

def save_config(assembly, samples):
    text = "Where to save the configuration file?"
    if display:
        config = PyZenity.GetSavename(default = 'config.json', title = title, text = text)[0]
        if config:
            with open(config, 'wt') as handle:
                json.dump({'assembly':assembly, 'samples':samples}, handle)
    else:
        d = dialog.Dialog(dialog = 'dialog' if not OS.startswith('win') else os.path.join(os.path.dirname(os.path.realpath(__file__)), 'windows', 'dialog.exe'), autowidgetsize = True)
        d.set_background_title("NSGmethDB API Client")
        code, config = d.fselect(os.path.join(os.getcwd(), 'config.json'), title = text)
        if code == d.OK and config:
            with open(config, 'wt') as handle:
                json.dump({'assembly':assembly, 'samples':samples}, handle)

def config_parser(configfile):
    data = json.load(configfile)
    return data['assembly'], data['samples']

def make_outdir(output):
    if not os.path.exists(output):
        os.makedirs(output)

def bed_reader(bedfile):
    csv_reader = csv.reader(bedfile, delimiter='\t')
    for row in csv_reader:
        try:
            region = row[0], str(int(row[1])+1), str(int(row[2]))
        except:
            logger.critical('INVALID BED FILE! Leaving the program...')
            raise SystemExit
        yield region

def get_total(bedfile):
    p = subprocess.Popen(['wc', '-l', bedfile.name], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    result, err = p.communicate()
    if p.returncode != 0:
        logger.critical('INVALID BED FILE! Leaving the program...')
        raise SystemExit
    return int(result.strip().split()[0])

def progress(bar, message, index, total):
    percentage = int((index / total) * 100)
    if display:
        bar(percentage, message)
    else:
        bar.gauge_update(text = message, percent = percentage, update_text = True)

def get_region(index, total, region, assembly, samples, output, server, bar):
    if index == 0 and not display:
        bar.gauge_start()
    logger.info('Getting data from region {}:{}-{}'.format(region[0], region[1], region[2]))
    progress(bar, 'Getting data from region {}:{}-{}'.format(region[0], region[1], region[2]), index, total)
    meth_ratio = collections.OrderedDict()
    for n in range(0, 11, 1):
        meth_ratio[n/10] = {}
        for sample in samples:
            meth_ratio[n/10][sample] = 0
    for sample in samples:
        meth_ratio[sample] = []
    query = region[0] + ":" + region[1] + "-" + region[2] + '?samples=' + ",".join(samples)
    url = os.path.join(server, assembly, query)
    logger.info('Methylation Levels and DMCs - GET: ' + url)
    n = 0
    while True:
        try:
            res = requests.get(url)
            break
        except:
            n += 1
            if n < retries:
                logger.warning('Internet connection failed. Retrying...')
            else:
                logger.critical('Unable to connect to the Internet! Leaving the program...')
                raise SystemExit
    if res.status_code != 200:
        logger.error('API Error: ' + str(res.status_code))
        logger.critical('Unable to reach the NGSmethDB API Server! Leaving the program...')
        raise SystemExit
    data = res.json()
    if not data:
        logger.warning('No data available in this region!')
        progress(bar, region, index + 1, total)
        return
    logger.info('Calculating...')
    meth_cg = os.path.join(output,'meth_cg', "_".join(region))
    stats = os.path.join(output, 'stats', "_".join(region))
    if not os.path.exists(meth_cg): os.makedirs(meth_cg)
    if not os.path.exists(stats): os.makedirs(stats)
    for sample in samples:
        with open(os.path.join(meth_cg, sample + '.tsv'), 'wt') as handle:
            header = ['#chrom', 'pos', 'genotype', 'w_methylatedReads', 'w_coverage', 'w_phredScore', 'c_methylatedReads', 'c_coverage', 'c_phredScore']
            header += ['methylatedReads', 'coverage', 'phredScore', 'w_methRatio', 'c_methRatio', 'methRatio']
            header = '\t'.join(header) + '\n'
            handle.write(header)
    for d in data:
        for sample in samples:
            individual, s = sample.split('.')
            line = [d['chrom'], d['pos'], d['genotype'][individual][s]]
            w_methylatedReads = d['meth_cg']['w']['methylatedReads'][individual][s]
            w_coverage = d['meth_cg']['w']['coverage'][individual][s]
            w_phredScore = d['meth_cg']['w']['phredScore'][individual][s]
            w_methRatio = round(w_methylatedReads/w_coverage, 2) if w_methylatedReads and w_coverage else None
            c_methylatedReads = d['meth_cg']['c']['methylatedReads'][individual][s]
            c_coverage = d['meth_cg']['c']['coverage'][individual][s]
            c_phredScore = d['meth_cg']['c']['phredScore'][individual][s]
            c_methRatio = round(c_methylatedReads/c_coverage, 2) if c_methylatedReads and c_coverage else None
            methylatedReads = sum(filter(None, [w_methylatedReads, c_methylatedReads]))
            coverage = sum(filter(None, [w_coverage, c_coverage]))
            if not w_phredScore:
                phredScore = c_phredScore
            elif not c_phredScore:
                phredScore = w_phredScore
            else:
                phredScore = int(sum([w_phredScore, c_phredScore])/2)
            methRatio = round(methylatedReads/coverage, 2)
            meth_ratio[round(methRatio, 1)][sample] += 1
            meth_ratio[sample].append(round(methRatio, 1))
            with open(os.path.join(meth_cg, sample + '.tsv'), 'at') as handle:
                line += [w_methylatedReads, w_coverage, w_phredScore, c_methylatedReads, c_coverage, c_phredScore, methylatedReads, coverage, phredScore, w_methRatio, c_methRatio, methRatio]
                line = [str(value) if value else '.' for value in line]
                line = '\t'.join(line) + '\n'
                handle.write(line)
        if len(samples) >= 2 and 'diffmeth_cg' in d:
            diffmeth_cg = os.path.join(output, 'diffmeth_cg', "_".join(region))
            if not os.path.exists(diffmeth_cg): os.makedirs(diffmeth_cg)
            intraindividual_file = os.path.join(diffmeth_cg, 'intraindividual.tsv')
            interindividual_file = os.path.join(diffmeth_cg, 'interindividual.tsv')
            has_intraindividual = False
            has_interindividual = False
            if not os.path.exists(intraindividual_file):
                with open(os.path.join(diffmeth_cg, 'intraindividual' + '.tsv'), 'wt') as handle:
                    header = ['chrom', 'pos', 'sample1', 'sample2', 'method', 'pvalue']
                    header = '\t'.join(header) + '\n'
                    handle.write(header)
            if not os.path.exists(interindividual_file):
                with open(os.path.join(diffmeth_cg, 'interindividual' + '.tsv'), 'wt') as handle:
                    header = ['chrom', 'pos', 'sample1', 'sample2', 'method', 'pvalue']
                    header = '\t'.join(header) + '\n'
                    handle.write(header)
            for pair in list(itertools.combinations(samples, 2)):
                tmp1, tmp2 = pair
                individual1, sample1 = tmp1.split('.')
                individual2, sample2 = tmp2.split('.')
                individual_pair = '#'.join([individual1, individual2])
                sample_pair = '#'.join([sample1, sample2])
                pair_kind = 'intraindividual' if individual1 == individual2 else 'interindividual'
                if individual_pair in d['diffmeth_cg']:
                    if sample_pair in d['diffmeth_cg'][individual_pair]:
                        if pair_kind == 'intraindividual':
                            has_intraindividual = True
                        else:
                            has_interindividual = True
                        with open(os.path.join(diffmeth_cg, pair_kind + '.tsv'), 'at') as handle:
                            pvalues = d['diffmeth_cg'][individual_pair][sample_pair]
                            for method in pvalues:
                                pvalue = pvalues[method]
                                line = [d['chrom'], d['pos'], tmp1, tmp2, method, pvalue]
                                line = [str(value) if value else '.' for value in line]
                                line = '\t'.join(line) + '\n'
                                handle.write(line)
            if not has_intraindividual:
                os.remove(intraindividual_file)
            if not has_interindividual:
                os.remove(interindividual_file)

    with open(os.path.join(stats, 'summary_stat.tsv'), 'wt') as handle:
        header = ['#measure'] + [sample for sample in samples]
        header = '\t'.join(header) + '\n'
        handle.write(header)
        if meth_ratio[sample]:
            line = ['average'] + [statistics.mean(meth_ratio[sample]) for sample in samples]
            line = [str(value) if value else '.' for value in line]
            line = '\t'.join(line) + '\n'
            handle.write(line)
            line = ['stdev'] + [statistics.stdev(meth_ratio[sample]) if len(meth_ratio[sample]) >=2 else '.' for sample in samples]
            line = [str(value) if value else '.' for value in line]
            line = '\t'.join(line) + '\n'
            handle.write(line)
            line = ['p10'] + [percentile(meth_ratio[sample], 0.1) for sample in samples]
            line = [str(value) if value else '.' for value in line]
            line = '\t'.join(line) + '\n'
            handle.write(line)
            line = ['p25'] + [percentile(meth_ratio[sample], 0.25) for sample in samples]
            line = [str(value) if value else '.' for value in line]
            line = '\t'.join(line) + '\n'
            handle.write(line)
            line = ['p50'] + [statistics.median(meth_ratio[sample]) for sample in samples]
            line = [str(value) if value else '.' for value in line]
            line = '\t'.join(line) + '\n'
            handle.write(line)
            line = ['p75'] + [percentile(meth_ratio[sample], 0.75) for sample in samples]
            line = [str(value) if value else '.' for value in line]
            line = '\t'.join(line) + '\n'
            handle.write(line)
            line = ['p90'] + [percentile(meth_ratio[sample], 0.9) for sample in samples]
            line = [str(value) if value else '.' for value in line]
            line = '\t'.join(line) + '\n'
            handle.write(line)
    with open(os.path.join(stats, 'histogram.tsv'), 'wt') as handle:
        header = ['#methRatio'] + [sample for sample in samples]
        header = '\t'.join(header) + '\n'
        handle.write(header)
        if meth_ratio[sample]:
            for n in range(0, 11, 1):
                n = n / 10
                line = [str(n)] + [meth_ratio[n][sample] for sample in samples]
                line = [str(value) if value else '0' for value in line]
                line = '\t'.join(line) + '\n'
                handle.write(line)
    logger.info('Done')
    # Methylation segments analysis
    query = region[0] + ":" + region[1] + "-" + region[2]
    url = os.path.join(os.path.join(server, 'segments', args.percentile), assembly, query)
    logger.info('Methylation segments - GET: ' + url)
    n = 0
    while True:
        try:
            res = requests.get(url)
            break
        except:
            n += 1
            if n < retries:
                logger.warning('Internet connection failed. Retrying...')
            else:
                logger.critical('Unable to connect to the Internet! Leaving the program...')
                raise SystemExit
    if res.status_code != 200:
        logger.error('API Error: ' + str(res.status_code))
        logger.critical('Unable to reach the NGSmethDB API Server! Leaving the program...')
        raise SystemExit
    data = res.json()
    if not data:
        logger.warning('No data available in this region!')
        progress(bar, region, index + 1, total)
        return
    logger.info('Calculating...')
    segments = os.path.join(output, 'segments')
    segments_dir = True
    if not os.path.exists(segments):
        segments_dir = False
        os.makedirs(segments)
    lines = []
    for d in data:
        for s in samples:
            individual, sample = s.split('.')
            if individual in d['samples']:
                if sample in d['samples'][individual]:
                    line = '\t'.join([d['chrom'], str(d['start']), str(d['end']), str(d['samples']['sampleCount']), s, str(d['samples'][individual][sample]['methRatio']), str(d['samples'][individual][sample]['cgCount'])]) + '\n'
                    lines.append(line)
    if lines:
        with open(os.path.join(segments, '_'.join(region) + '.tsv'), 'wt') as handle:
            handle.write('#chrom\tstart\tend\tsampleCount\tsample\tsample.methRatio\tsample.cgCount\n')
            handle.writelines(lines)
    logger.info('Done')
    # /Methylation segments analysis
    progress(bar, 'Done', index + 1, total)
    if index == total - 1 and not display:
        bar.gauge_stop()

def finish():
    message = 'Work done. Leaving the program...'
    logger.info(message)
    if display:
        bar = PyZenity.Progress(title = title, text = message, percentage = 0, auto_close = True)
        total = 10
        for index in range(1,11):
            progress(bar, message, index, total)
            time.sleep(1)
    else:
        bar = dialog.Dialog(dialog = 'dialog' if not OS.startswith('win') else os.path.join(os.path.dirname(os.path.realpath(__file__)), 'windows', 'dialog.exe'), autowidgetsize = False)
        bar.pause(text = message, seconds = 10, no_cancel = True)

def main(args):

    if args.config:
        assembly, samples = config_parser(args.config)
    else:
        logger.warning("No configuration file given! Asking for some options...")
        welcome(display)
        assembly = get_assembly(args.server)
        samples = get_samples(assembly, args.server)
        save_config(assembly, samples)

    index = 0
    total = get_total(args.input)
    logger.info("Number of regions in BED file: {}".format(total))

    if not display:
        bar = dialog.Dialog(dialog = 'dialog' if not OS.startswith('win') else os.path.join(os.path.dirname(os.path.realpath(__file__)), 'windows', 'dialog.exe'), autowidgetsize = False)
        bar.set_background_title("NSGmethDB API Client")
    else:
        bar = PyZenity.Progress(title = title, text = 'Initialising...', percentage = 0, auto_close = True)

    for region in bed_reader(args.input):
        get_region(index, total, region, assembly, samples, args.output, args.server, bar)
        index += 1

    finish()

if __name__ == '__main__':

    import argparse, logging, os, sys

    parser = argparse.ArgumentParser(prog='NGSmethDB API Client')
    parser.add_argument('-i', '--input', type=argparse.FileType('r'), help='\x1b[33mBED File (mandatory)\x1b[0m')
    parser.add_argument('-o', '--output', type=str, help='\x1b[33mOutput Directory (mandatory)\x1b[0m')
    parser.add_argument('-c', '--config', type=argparse.FileType('r'), help='\x1b[33mConfiguration File (optional)\x1b[0m')
    parser.add_argument('-r', '--server', type=str, default='http://bioinfo2.ugr.es:8888/NGSmethAPI', help='NGSmethDB API Server')
    parser.add_argument('-d', '--dialog', action='store_true', help='Do not try to use Zenity. Use dialog instead')
    parser.add_argument('-p', '--percentile', type=str, default='95', help='Methylation segments percentile threshold')
    parser.add_argument('--version', action='version', version='%(prog)s 0.1.0')
    global args
    args = parser.parse_args()

    if not args.input or not args.output:
        parser.print_help()
        raise SystemExit

    global title
    title = 'NGSmethDB API Client'

    global retries
    retries = 10

    global display
    display = 'DISPLAY' in os.environ
    if args.dialog: display = False

    if args.output: make_outdir(args.output)

    logger = logging.getLogger('NGSmethDB API Client')
    logger.setLevel(logging.DEBUG)
    fh = logging.FileHandler(os.path.join(args.output if args.output else os.getcwd(), 'NGSmethDB_API_client.log'))
    fh.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(logging.ERROR)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    logger.addHandler(fh)
    logger.addHandler(ch)

    python_version = sys.version_info[:3]
    logger.info('Python version: {}'.format('.'.join([str(i) for i in python_version])))
    if (python_version < (3, 4)):
        logger.critical('Python version not supported! Leaving the program...')
        raise SystemExit

    import shutil, time, subprocess, json, csv, itertools, collections, statistics, math, functools, dialog, PyZenity, requests

    global OS
    OS = sys.platform
    logger.info('OS / platform: {}'.format(OS))

    main(args)
