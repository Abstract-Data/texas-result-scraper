from nameparser import HumanName


def set_office_type(cls, values):
    if "PRESIDENT" in values['ON']:
        values['office_type'] = "POTUS"
    elif "U. S. SENATOR" in values['ON']:
        values['office_type'] = "US Senate"
    elif "GOVERNOR" in values['ON']:
        values['office_type'] = "Governor"
    elif "STATE SENATOR" in values['ON']:
        values['office_type'] = "SD"
    elif "STATE REPRESENTATIVE" in values['ON']:
        values['office_type'] = "HD"
    elif "U. S. REPRESENTATIVE" in values['ON']:
        values['office_type'] = "CD"
    elif "STATE BOARD OF EDUCATION" in values['ON']:
        values['office_type'] = "SBOE"
    elif "COURT OF CRIMINAL APPEALS" in values['ON']:
        _values = values['ON'].split(",")
        _office = None
        if "PLACE" in values['ON']:
            _office = "CCA " + " ".join(_values[1].split(" ")[-2:])
            if "CHIEF" in values['ON']:
                _office = "CJ" + _values[1].split(" ")[0] + " CCA" + _values[-2:]
        if "PRESIDING" in values['ON']:
            _office = "PJCCA"
        values['office_type'] = _office

    elif "COURT OF APPEALS" in values['ON']:
        _values = values['ON'].split(",")
        _office = None
        if "PLACE" in values['ON']:
            if "DISTRICT" in values['ON']:
                _office = _values[1].split(" ")[1] + " COA" + _values[2]
            if "CHIEF" in values['ON']:
                _office = "CJ " + _values[1].split(" ")[0] + " COA" + _values[2]
        elif "CHIEF" in values['ON']:
            if "DISTRICT" in values['ON']:
                _office = "CJ " + _values[1].split(" ")[1] + " COA"
            else:
                _office = "CJ " + _values[1].split(" ")[0] + " COA"
        elif "PRESIDING" in values['ON']:
            _office = "PJCOA"
        else:
            _office = _values[1].split(" ")[0] + "COA"
        values['office_type'] = _office
    elif "JUDICIAL DISTRICT" in values['ON']:
        _values = values['ON'].split(",")
        _split = [x.strip() for x in _values[1].split(" ")]
        if "DISTRICT ATTORNEY" in values['ON']:
            # TODO: Fix to handle 'DISTRICT ATTORNEY FOR KLEBERG AND KENEDY COUNTIES'
            # TODO: Fix to handle 'CRIMINAL DISTRICT ATTORNEY WALLER COUNTY - UNEXPIRED TERM'
            values['office_type'] = f"DA, {_values[1].split(' ')[1]} JD"  # OUTPUT Ex: DA, 123TH JD
        else:
            values['office_type'] = _split[0] if len(_split) == 3 else " ".join(_split[:3]) + " JD"
    elif "COUNTY DISTRICT ATTORNEY" in values['ON']:
        _values = values['ON'].split(" ")
        values['office_type'] = ' '.join(_values[:1]) + " DA"
    # elif "DISTRICT ATTORNEY" in values['ON']:
    #     if "JUDICIAL DISTRICT" in values['ON']:
    #         _values = values['ON'].split(",")
    #         values['office_type'] = f"DA, {_values[0].split(' ')[0]} JD"
    elif "CRIMINAL DISTRICT ATTORNEY" in values['ON']:
        if "- UNEXPIRED TERM" in values['ON']:
            _values = values['ON'].split(" ")
            values['office_type'] = ' '.join(_values[1:-3]) + " CDA"
        else:
            _values = values['ON'].split(" ")
            values['office_type'] = f"CDA {' '.join(_values[-2:])}"
    elif "MULTICOUNTY COURT AT LAW" in values['ON']:
        _values = values['ON'].split(" ")
        values['office_type'] = _values[0] + " MCL"
    elif "RAILROAD COMMISSIONER" in values['ON']:
        values['office_type'] = "RRC"
    elif "SUPREME COURT" in values['ON']:
        _values = values['ON'].split(",")
        values['office_type'] = "SCOTX" + _values[2]
    else:
        values['office_type'] = "Other"
    return values


def set_district_number(cls, values):
    if "DISTRICT" in values['ON']:
        _office_num = values['ON'].split(" ")[-1]
        if _office_num.isdigit():
            values['office_district_number'] = int(_office_num)
    return values


def parse_candidate_name(self):
    name = HumanName(self.full_name)
    print(name)
    self.first_name = name.first
    self.last_name = name.last
    return self
