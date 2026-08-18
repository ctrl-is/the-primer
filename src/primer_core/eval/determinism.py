from __future__ import annotations

import builtins
from copy import deepcopy
from typing import Any, NamedTuple

from pydantic import BaseModel

from primer_core.eval.cases import EngagementEvalCase
from primer_core.eval.metrics import find_eval_case


async def assert_orchestrator_deterministic(domains: list[str]) -> None:
    """
    Asserts that multiple EngagementOrchestrator objects with the same input conditions
    (as dictated by the EngagementEvalCase objects) will all be semantically identical
    within both the 'education' and 'coop-finance' domains.
    """

    def attributes(variables: dict) -> dict:
        """
        Recusrively decomposes an [attribute name]: [attribute value] dictionary of an
        object into a dictionary in which all the values that are instances of custom
        classes are decomposed into similar [attribute name]: [attribute value] dictionaries.

        This allows objects (in this case, orchestrators) to be compared semantically
        (i.e, using `==`) despite the objects' attributes potentially differing only
        by the spaces in memory they occupy.
        """
        variables_copy = deepcopy(variables)

        def valid_class(obj: Any):
            return obj.__class__.__name__ in dir(builtins) + ["NoneType", "UUID"]

        def custom_class_to_dict(obj: Any) -> dict:
            # If the attribute is not in builtins, it can be assumed that it is a custom class
            if isinstance(obj, BaseModel):
                return obj.model_dump()
            elif NamedTuple in obj.__class__.__bases__:
                return obj._asdict()
            else:
                return vars(obj)

        for name, value in variables_copy.items():
            if not valid_class(value):
                value_dict = custom_class_to_dict(value)
                variables_copy[name] = attributes(value_dict)
                # ^ Converts custom class object into a dict of its attributes
                #   (able to be semantically compared)
            elif isinstance(value, list):
                new_value_list = []
                for obj in value:
                    if not valid_class(obj):
                        obj_dict = custom_class_to_dict(obj)
                        new_value_list.append(attributes(obj_dict))
                    else:
                        new_value_list.append(obj)
                variables_copy[name] = new_value_list

        return variables_copy

    for domain in domains:
        cases: list[EngagementEvalCase] = [find_eval_case(domain) for _ in range(5)]

        for case in cases:
            await case.orchestrator.run_engagement(
                skill_name=case.skill_name,
                subject_id=case.subject_id,
                thread_id=case.thread_id,
            )

        base_orchestrator_attr = attributes(vars(cases[0].orchestrator))
        assert all(
            attributes(vars(case.orchestrator)) == base_orchestrator_attr for case in cases
        ), (
            f"Identical EngagementOrchestrator objects for the domain {domain} "
            "differ in their attributes."
        )
