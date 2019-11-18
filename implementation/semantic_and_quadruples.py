# Semantic checks and quadruple generation for MALI language.

from implementation.utils.semantic_and_quadruples_utils import *  # pylint: disable=unused-wildcard-import
from implementation.utils.generic_utils import *
from implementation.utils.constants import *
import re

# Semantic table filling.

classes = {'#global': new_class_dict(name='#global', parent=None)}

current_class = classes['#global']
current_function = current_class['#funcs']['#attributes']
current_access = Access.PUBLIC
current_type = None
is_param = False
param_count = 0
var_avail = Available(VAR_LOWER_LIMIT, VAR_UPPER_LIMIT)
temp_avail = Available(TEMP_LOWER_LIMIT, TEMP_UPPER_LIMIT)


def seen_class(class_name):
  if class_name in classes:
    return f"Repeated class name: {class_name}"
  else:
    global current_class, current_function
    classes[class_name] = new_class_dict(class_name)
    current_class = classes[class_name]
    current_function = current_class['#funcs']['#attributes']


def class_parent(class_parent):
  if class_parent not in classes:
    return f"Undeclared class parent: {class_parent}"
  else:
    current_class['#parent'] = class_parent


def finish_class():
  global current_class, current_function, current_access, var_avail, temp_avail
  current_class = classes['#global']
  current_function = current_class['#funcs']['#attributes']
  current_access = Access.PUBLIC
  var_avail = Available(VAR_LOWER_LIMIT, VAR_UPPER_LIMIT)
  temp_avail = Available(TEMP_LOWER_LIMIT, TEMP_UPPER_LIMIT)


def seen_func(func_name):
  global func_size, current_class, current_function, var_avail, temp_avail
  func_size = 0
  if func_name in current_class['#funcs']:
    return f"Redeclared function {func_name}"
  else:
    current_class['#funcs'][func_name] = new_func_dict(func_name, current_type)
    current_function = current_class['#funcs'][func_name]
  var_avail = Available(VAR_LOWER_LIMIT, VAR_UPPER_LIMIT)
  temp_avail = Available(TEMP_LOWER_LIMIT, TEMP_UPPER_LIMIT)


def seen_access(new_access):
  global current_access
  current_access = new_access


def seen_type(new_type):
  global current_type
  if new_type not in func_types and (
          new_type not in classes):
    return f"{new_type} is not a class nor data type"
  current_type = new_type


def var_name(var_name):
  global param_count
  if var_name in current_function['#vars']:
    return f"Redeclared variable: {var_name}"
  else:
    address = var_avail.next(current_type)
    if not address:
      return 'Too many variables.'
    adjust = 0
    if current_function['#name'] == '#attributes':
      adjust = ATTRIBUTES_ADJUSTMENT
      if current_class['#name'] == '#global':
        adjust = GLOBAL_ADJUSTMENT

    current_function['#vars'][var_name] = (
        new_var_dict(current_type, address-adjust, current_access))

    if is_param:
      current_function['#param_count'] += 1
      current_function['#vars'][var_name]['#assigned'] = True
    else:
      current_function['#var_count'] += 1


def switch_param(reading_params):
  global is_param
  is_param = reading_params


def set_access():
  global current_function
  current_function['#access'] = current_access


# Intermediate code generation.

operators = []
types = []
operands = []
quadruples = [[Operations.GOTO.value, None, None, None]]
visual_quadruples = [[Operations.GOTO.name, None, None, None]]
jumps = []
pending_returns = []
q_count = 1
const_avail = Available(CONSTANT_LOWER_LIMIT, CONSTANT_UPPER_LIMIT,
                        avail_types)
constant_addresses = {}
calling_class = current_class
calling_function = []
passing_params = False
called_attribute = None
expecting_init = False
calling_parent = False


def address_or_else(operand, is_visual=False):
  if operand is not None:
    if isinstance(operand, Operand):
      if is_visual:
        return operand.get_raw()
      else:
        return operand.get_address()
    else:
      return operand
  return None


def generate_quadruple(a, b, c, d):
  global q_count, quadruples, visual_quadruples

  left_operand = address_or_else(b)
  right_operand = address_or_else(c)
  result = address_or_else(d)

  quadruples.append([a.value, left_operand, right_operand, result])
  q_count += 1

  v_left_operand = address_or_else(b, True)
  v_right_operand = address_or_else(c, True)
  v_result = address_or_else(d, True)
  visual_quadruples.append([a.name, v_left_operand, v_right_operand, v_result])


def find_and_populate(operand, prefix, access, check_assigned_var=False,
                      mark_assigned=False, check_init_called=False):
  global expecting_init
  raw_operand = operand.get_raw()
  var = prefix.get(raw_operand, None)
  if not var:
    return False
  if check_init_called:
    if not var['#assigned']:
      expecting_init = True
      var['#assigned'] = True
  if check_assigned_var:
    if mark_assigned:
      var['#assigned'] = True
    elif not var['#assigned']:
      operand.set_error(f'Variable {raw_operand} used before assignment.')
      return True
  if var['#access'] not in access:
    operand.set_error(f'Variable {raw_operand} cannot be accessed.')
    return True
  else:
    operand.set_type(var['#type'])
    operand.set_address(var['#address'])
    return True


def populate_call(operand, check_init_called=True):
  # Search for var in the attributes of the class and its parents.
  curr_class = calling_class['#name']
  while curr_class:
    class_attributes = classes[curr_class]['#funcs']['#attributes']['#vars']
    if find_and_populate(operand, class_attributes, [Access.PUBLIC], False,
                         False, check_init_called):
      return
    curr_class = classes[curr_class]['#parent']

  if not operand.get_error():
    operand.set_error(f'{operand.get_raw()} not in scope.')


def populate_local_var(operand, mark_assigned=False, is_instance=False):
  # Search for var in function's local vars.
  check_assigned_var = not is_instance
  function_vars = current_function['#vars']
  if find_and_populate(operand, function_vars,
                       [Access.PUBLIC, Access.PROTECTED, Access.PRIVATE],
                       check_assigned_var, mark_assigned, is_instance):
    return
  # Search for var in the attributes from the class.
  class_attributes = current_class['#funcs']['#attributes']['#vars']
  if find_and_populate(operand, class_attributes,
                       [Access.PUBLIC, Access.PROTECTED, Access.PRIVATE],
                       check_assigned_var, mark_assigned, is_instance):
    return
  # Search for var in the attributes of inherited classes.
  curr_class = current_class['#parent']
  while curr_class:
    class_attributes = classes[curr_class]['#funcs']['#attributes']['#vars']
    if find_and_populate(operand, class_attributes,
                         [Access.PUBLIC, Access.PROTECTED],
                         check_assigned_var, mark_assigned, is_instance):
      return
    curr_class = classes[curr_class]['#parent']

  if not operand.get_error():
    operand.set_error(f'Variable {operand.get_raw()} not in scope.')


def get_or_create_cte_address(value, val_type):
  global constant_addresses
  if value in constant_addresses:
    return constant_addresses[value]
  else:
    address = const_avail.next(val_type)
    constant_addresses[value] = address
    return address


def find_and_build_operand(raw_operand, mark_assigned=False):
  t = type(raw_operand)
  operand = Operand(raw_operand)
  if t == int:
    address = get_or_create_cte_address(raw_operand, Types.INT)
    if not address:
      operand.set_error('Too many int constants.')
    operand.set_type(Types.INT)
    operand.set_address(address)
  elif t == float:
    address = get_or_create_cte_address(raw_operand, Types.FLOAT)
    if not address:
      operand.set_error('Too many float constants.')
    operand.set_type(Types.FLOAT)
    operand.set_address(address)
  # TODO: This might not occur.
  elif t == bool:
    address = get_or_create_cte_address(raw_operand, Types.BOOL)
    if not address:
      operand.set_error('Too many bool constants.')
    operand.set_type(Types.BOOL)
    operand.set_address(address)
  elif t == str:
    if re.match(r"\'.\'", raw_operand):
      address = get_or_create_cte_address(raw_operand[1:-1], Types.CHAR)
      if not address:
        operand.set_error('Too many char constants.')
      operand.set_type(Types.CHAR)
      operand.set_address(address)
      operand.set_raw(raw_operand[1:-1])
    else:
      populate_local_var(operand, mark_assigned)
  return operand


def register_operand(raw_operand, mark_assigned=False):
  global operands, types
  operand = find_and_build_operand(raw_operand, mark_assigned)
  if operand.get_error():
    return operand.get_error()
  operands.append(operand)
  types.append(operand.get_type())


def register_operator(operator):
  global operators
  operators.append(operator)


def build_temp_operand(op_type, assignable=False):
  global current_function
  operand = Operand()
  address = temp_avail.next(op_type)
  if not address:
    operand.set_error('Too many variables.')
  current_function['#vars'][address] = new_var_dict(
      op_type, address, assigned=True)
  current_function['#var_count'] += 1
  operand.set_address(address)
  operand.set_type(op_type)
  operand.set_raw(operand.get_address())
  return operand


def solve_operation_or_continue(ops):
  global operators, operands, types
  operator = top(operators)
  if operator in ops:
    right_operand = operands.pop()
    right_type = types.pop()
    left_operand = operands.pop()
    left_type = types.pop()
    operator = operators.pop()
    result_type = semantic_cube[left_type][right_type][operator]
    if not result_type:
      if left_type == Types.VOID or right_type == Types.VOID:
        return f'Expression returns no value.'
      return (f'Type mismatch: Invalid operation {operator} on given operands')
    temp = build_temp_operand(result_type)
    if temp.get_error():
      return temp.get_error()
    generate_quadruple(operator, left_operand, right_operand, temp)
    operands.append(temp)
    types.append(result_type)


def pop_fake_bottom():
  global operators
  operators.pop()


def do_assign():
  global operators, operands, types
  left_operand = operands.pop()
  left_type = types.pop()
  assigning_operand = operands.pop()
  assigning_type = types.pop()
  if not semantic_cube[assigning_type][left_type][Operations.EQUAL]:
    if left_type == Types.VOID:
      return f'Expression returns no value.'
    return (f'Type mismatch: expression cannot be assigned')
  generate_quadruple(Operations.EQUAL, left_operand, None, assigning_operand)
  operands.append(assigning_operand)
  types.append(assigning_type)


def do_write(s=None):
  global operands, types
  if s:
    operand = Operand(s[1:-1])
    operand.set_type(Types.CTE_STRING)
    operand.set_address(s[1:-1])
  else:
    operand = operands.pop()
    op_type = types.pop()
    if op_type not in var_types:
      return f'Expression returns no value.'
  generate_quadruple(Operations.WRITE, None, None, operand)


def do_read():
  global operands, types
  operand = Operand('read')
  operand.set_address('read')
  operand.set_type(Types.READ)
  operands.append(operand)
  types.append(Types.READ)


def register_condition():
  global operands, types
  exp_type = types.pop()
  if exp_type != Types.BOOL:
    return 'Evaluated expression is not boolean'
  result = operands.pop()
  generate_quadruple(Operations.GOTOF, result, None, None)
  jumps.append(q_count-1)


def register_else():
  generate_quadruple(Operations.GOTO, None, None, None)
  false = jumps.pop()
  jumps.append(q_count-1)
  quadruples[false][3] = q_count


def register_end_if():
  end = jumps.pop()
  quadruples[end][3] = q_count


def register_while():
  jumps.append(q_count)


def register_end_while():
  end = jumps.pop()
  quadruples[end][3] = q_count+1
  ret = jumps.pop()
  generate_quadruple(Operations.GOTO, None, None, ret)


def register_function_beginning():
  current_function['#start'] = q_count


def set_current_type_void():
  global current_type
  current_type = Types.VOID


def register_main_beginning():
  quadruples[0][3] = q_count
  visual_quadruples[0][3] = q_count


def register_func_end(is_main=False):
  global pending_returns
  if current_function['#type'] != Types.VOID and len(pending_returns) == 0:
    return f"No return statement on non-void function {current_function['#name']}"
  while len(pending_returns):
    quadruples[pending_returns.pop()][3] = q_count

  if is_main:
    generate_quadruple(Operations.END, None, None, None)
  else:
    generate_quadruple(Operations.ENDPROC, None, None, None)


def register_return():
  global operands, types, pending_returns
  function_type = current_function['#type']
  if function_type == Types.VOID:
    return 'Void function cannot return a value'
  return_val = operands.pop()
  return_type = types.pop()
  if not semantic_cube[function_type][return_type][Operations.EQUAL]:
    return f'Cannot return type {return_type} as {function_type}'
  pending_returns.append(q_count)
  generate_quadruple(Operations.RETURN, return_val, None, None)


def call_parent(parent):
  global calling_class, calling_function, calling_parent
  if not current_class['#parent']:
    return (f"{current_class['#name']} has no parent class but tries "
            + f'to extend {parent} in constructor')
  elif parent != current_class['#parent']:
    return f"{parent} is not {current_class['#name']}'s parent"
  calling_parent = True
  calling_class = classes[parent]
  calling_function.append(calling_class['#funcs']['init'])


def finish_parent_call():
  global calling_class, calling_function, operands, types
  calling_class = current_class
  calling_function.pop()
  # TODO: Verificar que lo siguiente es necesario
  operands.append(Types.VOID)
  types.append(Types.VOID)


class_call_stack = [[]]
func_call_stack = []
params_stack = []


def switch_instance(instance_name):
  global calling_class
  instance = Operand(instance_name)
  if len(class_call_stack[-1]) == 0:
    populate_local_var(instance, is_instance=True)
  else:
    calling_class = classes[class_call_stack[-1][-1]]
    print(class_call_stack, instance_name)
    populate_call(instance)

  if instance.get_error():
    return instance.get_error()

  class_call_stack[-1].append(instance.get_type())
  print(instance.get_type())


def seen_instance_attribute(attribute_name):
  global calling_class
  attribute = Operand(attribute_name)
  calling_class = classes[class_call_stack[-1][-1]]
  populate_call(attribute)

  if attribute.get_error():
    return attribute.get_error()

  for instance in class_call_stack[-1]:
    generate_quadruple(Operations.ENTER_INSTANCE, instance,
                       None, class_call_stack[-1][-1])

  generate_quadruple(Operations.RETURN, attribute, None, None)

  while len(class_call_stack[-1]) > 0:
    generate_quadruple(Operations.EXIT_INSTANCE, None, None, None)
    class_call_stack[-1].pop()

  temp = build_temp_operand(attribute.get_type())
  generate_quadruple(Operations.GET_RETURN, temp, None, q_count+1)

  operands.append(attribute)
  types.append(attribute.get_type())


# TODO: Llevar arriba donde estan las demas busquedas
def populate_func_call(operand, is_init=False):
  global expecting_init
  func_name = operand.get_raw()

  if is_init:
    expecting_init = False
  curr_class = calling_class['#name']
  while curr_class:
    if func_name in classes[curr_class]['#funcs']:
      if classes[curr_class]['#funcs'][func_name]['#access'] != Access.PUBLIC:
        return f"Cannot access {calling_function[-1]['#name']}."
      operand.set_type(classes[curr_class]['#funcs'][func_name]['#type'])
      return
  return f'{func_name} not defined in scope.'


def seen_instance_func(func_name, is_init=False):
  global calling_class
  func = Operand(func_name)
  calling_class = classes[class_call_stack[-1][-1]]
  populate_func_call(func, is_init=is_init)

  if func.get_error():
    return func.get_error()

  func_call_stack.append(classes[class_call_stack[-1][-1]]['#funcs'][func_name])


def start_passing_params():
  params_stack.append([])
  class_call_stack.append([])


def register_param():
  # print(top(operands).get_raw())
  params_stack[-1].append(operands.pop())


def done_passing_params():
  global pending_returns

  if len(class_call_stack[-1]) > 0:
    for instance in class_call_stack[-1]:
      generate_quadruple(Operations.ENTER_INSTANCE, instance,
                        None, class_call_stack[-1][-1])
    calling = class_call_stack[-1][-1]
  else:
    calling = current_class['#name']
  generate_quadruple(Operations.ERA, calling,
                    func_call_stack[-1]['#name'], None)

  expecting_params = func_call_stack[-1]['#param_count']
  assigning_params = list(func_call_stack[-1]['#vars'].values())
  if len(params_stack[-1])+1 != expecting_params:
    return (f"{func_call_stack[-1]['#name']} expects {expecting_params}, but "
            + f'{len(params_stack[-1])+1} were given')
  count = 0
  for sending_param in params_stack[-1]:
    if not semantic_cube[assigning_params[count]][sending_param.get_type()][Operations.EQUAL]:
      return (f'Incompatible param {count+1} on call to ' +
          f"{func_call_stack[-1]['#name']}")
    generate_quadruple(Operations.PARAM, sending_param, None, count)
    count += 1
  params_stack.pop()

  generate_quadruple(Operations.GOSUB, None, None, None)

  while len(class_call_stack[-1]) > 0:
    generate_quadruple(Operations.EXIT_INSTANCE, None, None, None)
    class_call_stack[-1].pop()
  class_call_stack.pop()
  print(class_call_stack)

  temp = build_temp_operand(func_call_stack[-1]['#type'])
  pending_returns.append(q_count+1)
  generate_quadruple(Operations.GET_RETURN, temp, None, None)
  Operands.append(temp)
  types.append(temp)

# def start_func_call(func_name):
#   global calling_class, calling_function
#   if len(calling_class) == 0:
#     calling_class.append(current_class)
#   if func_name in calling_class[-1]['#funcs']:
#     calling_function.append(calling_class[-1]['#funcs'][func_name])
#     return
#   curr_class = calling_class[-1]['#parent']
#   while curr_class:
#     if func_name in classes[curr_class]['#funcs']:
#       calling_class.append(classes[curr_class])
#       calling_function.append(calling_class[-1]['#funcs'][func_name])
#       if calling_function[-1]['#access'] not in [Access.PUBLIC, Access.PROTECTED]:
#         return f"Cannot access {calling_function[-1]['#name']}."
#       return
#     curr_class = classes[curr_class]['#parent']
#   return f'{func_name} not defined in scope.'


# def start_instance_func_call(func_name, is_init=False):
#   global calling_class, calling_function, expecting_init
#   if is_init:
#     expecting_init = False
#   curr_class = calling_class[-1]['#name']
#   calling_class.pop()
#   while curr_class:
#     if func_name in classes[curr_class]['#funcs']:
#       calling_class.append(classes[curr_class])
#       calling_function.append(calling_class[-1]['#funcs'][func_name])
#       if calling_function[-1]['#access'] != Access.PUBLIC:
#         return f"Cannot access {calling_function[-1]['#name']}."
#       return
#     curr_class = classes[curr_class]['#parent']
#   return f'{func_name} not defined in scope.'


# def start_param_collection():
#   global param_count, calling_parent, passing_params
#   param_count = 0
#   generate_quadruple(Operations.ERA, calling_class[-1]['#name'],
#                      calling_function[-1]['#name'], calling_parent)
#   passing_params = True
#   calling_class.append(Operations.FAKE_BOTTOM)


# def pass_param():
#   global operands, types
#   param = list(calling_function[-1]['#vars'].values())[param_count]
#   param_type = param['#type']
#   argument = operands.pop()
#   arg_type = types.pop()
#   if not semantic_cube[arg_type][param_type][Operations.EQUAL]:
#     return (f"{calling_function[-1]['#name']} expecting type {param_type.value} "
#             + f'for parameter {param_count+1}')
#   generate_quadruple(Operations.PARAM, argument, None, param_count)


# def prepare_upcoming_param():
#   global param_count
#   param_count += 1
#   expected = calling_function[-1]['#param_count']
#   if param_count+1 > expected:
#     return (f"{calling_function[-1]['#name']} expects {expected} parameters, " +
#             'but more were given')


# def done_param_pass():
#   global passing_params
#   calling_class.pop()  # Pop fake bottom
#   passing_params = False
#   expected = calling_function[-1]['#param_count']
#   if param_count+1 != expected and not param_count == 0 and not expected == 0:
#     return (f"{calling_function[-1]['#name']} expects {expected} parameters, " +
#             f'but {param_count+1} were given')
#   generate_quadruple(
#       Operations.GOSUB, calling_class[-1]['#name'], calling_function[-1]['#name'], None)


# def instance_attribute_call(attribute):
#   global calling_function, called_attribute
#   if expecting_init:
#     return 'Calling class member before calling init.'
#   calling_function.append(calling_class[-1]['#funcs']['#attributes'])
#   called_attribute = Operand(attribute)
#   populate_call(called_attribute)
#   if called_attribute.get_error():
#     return called_attribute.get_error()
#   generate_quadruple(Operations.RETURN, called_attribute, None, q_count+1)


# def finish_call():
#   global calling_class, calling_function, operands, types, calling_class

#   while top(calling_class) and top(calling_class) != Operations.FAKE_BOTTOM:
#     generate_quadruple(Operations.EXIT_INSTANCE, None, None, None)
#     calling_class.pop()

#   if calling_function[-1]['#name'] == '#attributes':
#     op_type = called_attribute.get_type()
#   else:
#     op_type = calling_function[-1]['#type']

#   if op_type == Types.VOID:
#     operands.append(Types.VOID)
#     types.append(Types.VOID)
#   else:
#     operand = build_temp_operand(op_type)
#     generate_quadruple(Operations.GET_RETURN, None, None,
#                        operand.get_address())
#     operands.append(operand)
#     types.append(operand.get_type())

#   calling_function.pop()


# def switch_func(func_name):
#   global calling_function
#   calling_function.append(calling_class[-1]['#funcs'][func_name])


# def switch_instance(instance):
#   global calling_class, calling_function, passing_params

#   if expecting_init:
#     return 'Calling class member before calling init.'

#   operand = Operand(instance)

#   if len(calling_class) > 0 and not passing_params:
#     populate_call(operand)
#   else:
#     populate_local_var(operand, is_instance=True)

#   class_type = operand.get_type()
#   if operand.get_error():
#     return operand.get_error()
#   elif class_type in var_types:
#     return f'{instance} is of type {class_type} and not an instance.'
#   generate_quadruple(Operations.ENTER_INSTANCE, operand, None, class_type)

#   calling_class.append(classes[class_type])


def generate_output():
  global classes

  data_segment = {}
  for v in classes['#global']['#funcs']['#attributes']['#vars'].values():
    if type(v['#type']) == str:
      var_type = v['#type']
    else:
      var_type = v['#type'].value
    data_segment[v['#address']] = var_type

  constant_segment = invert_dict(constant_addresses)

  # Clean symbol table for use in virtual machine.
  for v1 in classes.values():
    if v1['#parent'] == '#global':
      v1['#parent'] = None
    for v2 in v1['#funcs'].values():
      v2['#type'] = v2['#type'].value
      if '#access' in v2:
        del v2['#access']
      for v3 in v2['#vars'].values():
        del v3['#assigned']
        if type(v3['#type']) != str:
          v3['#type'] = v3['#type'].value
        if '#access' in v3:
          del v3['#access']

  del classes['#global']['#funcs']['#attributes']

  return {
      'symbol_table': classes,
      'data_segment': data_segment,
      'constant_segment': constant_segment,
      'quadruples': quadruples
  }
