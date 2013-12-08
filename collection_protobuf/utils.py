
def msg(pb, **kwargs):
    for key, item in kwargs.iteritems():
        setattr(pb, key, item)
    return pb

def append_msg(repeated, **kwargs):
    pb = repeated.add()
    return msg(pb, **kwargs)
