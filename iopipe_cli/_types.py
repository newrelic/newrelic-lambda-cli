# From pep-0318 examples:
# https://www.python.org/dev/peps/pep-0318/#examples


def accepts(*types):
    def check_accepts(f):
        assert len(types) == f.func_code.co_argcount

        def new_f(*args, **kwds):
            for (a, t) in zip(args, types):
                assert isinstance(a, t), "arg %r does not match %s" % (a, t)
            return f(*args, **kwds)

        new_f.func_name = f.func_name
        return new_f

    return check_accepts


def returns(rtype):
    def check_returns(f):
        def new_f(*args, **kwds):
            result = f(*args, **kwds)
            assert isinstance(result, rtype), "return value %r does not match %s" % (
                result,
                rtype,
            )
            return result

        new_f.func_name = f.func_name
        return new_f

    return check_returns


# Example usage:
# @accepts(int, (int,float))
# @returns((int,float))
# def func(arg1, arg2):
#    return arg1 * arg2
