#!/usr/bin/env python

from visualCaseGen.cime_interface import CIME_interface

cime = CIME_interface()

def rn(s):
    """Remove numeric characters from a string."""
    return ''.join([i for i in s if not i.isdigit()])


def get_models(compset_lname):
    """Given a compset lname, return the list of models that are coupled."""
    compset_components = cime.get_components_from_compset_lname(compset_lname)
    model_list = []
    for comp_class, compset_component in compset_components.items():
        if not compset_component.startswith('X'):
            phys = compset_component.split('%')[0]
            model = next((model for model in cime.models[comp_class] if phys in cime.comp_phys[model]), None)
            model_list.append(model)
    return model_list

def compset_pattern_finder():
    """Find the models that are never coupled and always coupled with each other.
    This is useful for identifying patterns and adding them as relational constraints."""

    all_models = {model for model_list in cime.models.values() for model in model_list if model[0] != 'x'}

    never = {model: all_models - {model} for model in all_models}
    always = {model: all_models - {model} for model in all_models}

    for compset in cime.compsets.values():

        compset_models = get_models(compset.lname)

        for model in compset_models:
            if model:
                never[model].difference_update(compset_models)
                always[model].intersection_update(compset_models)
    

    # From never, remove the models that are in the same component class as the model:
    for model, never_coupled in never.items():
        comp_class = None
        for cc, models in cime.models.items():
            if model in models:
                comp_class = cc
                break
        if comp_class:
            never[model] = never_coupled - set(cime.models[comp_class])

    # Print the results
    print('Never coupled:')
    print('----------------------------------------')
    for model, never_coupled in never.items():
        if never_coupled:
            print(f'{model}: {never_coupled}')

    print('\nAlways coupled:')
    print('----------------------------------------')
    for model, always_coupled in always.items():
        if always_coupled:
            print(f'{model}: {always_coupled}')


if __name__ == '__main__':
    compset_pattern_finder()
