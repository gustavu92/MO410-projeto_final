from .parser import parser_sample, parser_RAfT


def add_proposal(proposal_id, collection):
    collection.insert_one({'proposta': proposal_id})

def add_experiment(proposal_id, collection, **kwargs):
    collection.update_one({'proposta': proposal_id}, { '$push': { 'experimentos': kwargs } } )

def choose_experiment(experiments):
    if len(experiments) > 1:
        n = 1
        print('There are more than one experiment in this proposal.') 
        for experiment in experiments:
            print('Experiment ', n, ',')
            for key, value in experiment.items():
                if key != 'amostras':
                    print('\t', key, ' : ', value)
            n += 1
        return str(int(input('Please choose one experiment ')) - 1)
    else:
        return '0'

def choose_sample(samples):
    if len(samples) > 1:
        n = 1
        print('There are more than one sample in this experiment.') 
        for sample in samples:
            print('Sample ', n, ',')
            for key, value in sample.items():
                if key != 'medidas':
                    print('\t', key, ' : ', value)
            n += 1
        return str(int(input('Please choose one sample ')) - 1)
    else:
        return '0'

def add_sample(proposal_id, collection, **kwargs):
    proposal = collection.find({'proposta': proposal_id})[0]
    idx = choose_experiment(proposal['experimentos'])
    key = 'experimentos.' + idx + '.amostras'
    collection.update_one({'proposta': proposal_id}, { '$push': { key: kwargs } } )

def add_measurements(proposal_id, collection, sample_path, RAfT_path):
    proposal = collection.find({'proposta': proposal_id})[0]
    idx_exp = choose_experiment(proposal['experimentos'])
    idx_sam = choose_sample(proposal['experimentos'][int(idx_exp)]['amostras'])

    args = parser_sample(sample_path)
    args['reconstructions'] = [parser_RAfT(RAfT_path)]

    key = 'experimentos.' + idx_exp + '.amostras.' + idx_sam + '.medidas'
    collection.update_one({'proposta': proposal_id}, { '$push': { key: args } } )
