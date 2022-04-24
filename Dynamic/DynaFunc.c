#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <funcobject.h>
#include <compile.h>
#include <structmember.h>
#include <sys/prctl.h>
#include <linux/seccomp.h>
#include <linux/filter.h>

static PyObject* DynaFunc_new(PyTypeObject *type, PyObject *args, PyObject *kwargs);

typedef struct {
	PyFunctionObject list;
	const char *source_code;
} DynaFuncObject;

static int
func_set_code(PyFunctionObject *op, PyObject *value, void *Py_UNUSED(ignored))
{
	Py_ssize_t nfree, nclosure;

	/* Not legal to del f.func_code or to set it to anything
	 * other than a code object. */
	if (value == NULL || !PyCode_Check(value)) {
		PyErr_SetString(PyExc_TypeError,
						"__code__ must be set to a code object");
		return -1;
	}

	if (PySys_Audit("object.__setattr__", "OsO",
					op, "__code__", value) < 0) {
		return -1;
	}

	nfree = PyCode_GetNumFree((PyCodeObject *)value);
	nclosure = (op->func_closure == NULL ? 0 :
			PyTuple_GET_SIZE(op->func_closure));
	if (nclosure != nfree) {
		PyErr_Format(PyExc_ValueError,
					 "%U() requires a code object with %zd free vars,"
					 " not %zd",
					 op->func_name,
					 nclosure, nfree);
		return -1;
	}
	Py_INCREF(value);
	Py_XSETREF(op->func_code,value);
	return 0;
}


const char* decorate_code(PyFunctionObject* self,const char* src)
{
	const char self_func_name[6]="dynaf",**arg_names;
	char *dst,*ptr,*ptr2;
	int self_func_arg_cnt,i,dst_len;
	PyCodeObject *self_func_code;
	PyTupleObject *self_func_varnames;
	self_func_code=(PyCodeObject*)self->func_code;
	//self_func_name=PyUnicode_AsUTF8(self->func_name);
	self_func_arg_cnt=self_func_code->co_argcount;
	self_func_varnames=self_func_code->co_varnames;
	arg_names=(const char**)malloc(sizeof(char*)*self_func_arg_cnt);
	dst_len=9+strlen(self_func_name);//def <func_name>(<...>):\n\t
	dst_len+=strlen(src);
	for(i=0;i<self_func_arg_cnt;i++)
	{

		arg_names[i]=PyUnicode_AsUTF8(PyTuple_GetItem(self_func_varnames,i));
		dst_len+=strlen(arg_names[i])+1;//<arg_name>,
	}
	//dst_len-- ++
	for(i=0;i<strlen(src);i++)
	{
		if(src[i]=='\n')
		dst_len++;
	}
	dst=(char*)malloc(dst_len);
	sprintf(dst,"def %s(",self_func_name);
	for(i=0;i<self_func_arg_cnt-1;i++)
	{
		strcat(dst,arg_names[i]);
		dst[strlen(dst)+1]='\0';
		dst[strlen(dst)]=',';
	}
	if(self_func_arg_cnt)
	strcat(dst,arg_names[i]);
	strcat(dst,"):\n\t");
	ptr=&dst[strlen(dst)];
	for(ptr2=src;*ptr2;ptr2++)
	{
		*ptr++=*ptr2;
		if(*ptr2=='\n')
		*ptr++='\t';
	}
	*ptr='\0';
	free(arg_names);
	arg_names=NULL;
	return dst;
}

static PyObject*
DynaFunc_set(DynaFuncObject *self, PyObject *arg)
{
	const char *source_code,*input_code;
	PyObject *target_code;
	PyObject *def_code;
	if(!PyUnicode_Check(arg))
	{
		PyErr_SetString(PyExc_TypeError, "parameter must be a string");
		return NULL;
	}
	input_code=PyUnicode_AsUTF8(arg);
	if(strstr(input_code,"getattr") || strstr(input_code,"lambda") || strstr(input_code,"def") || strstr(input_code,"os") || strstr(input_code,"open"))
	{
		PyErr_SetString(PyExc_TypeError, "Bad code");
		return NULL;
	}

	source_code=decorate_code(&(self->list),input_code);
	def_code=Py_CompileStringExFlags(source_code,"not_exists",Py_file_input,(PyCompilerFlags*)NULL,2);
	if(!def_code)
	{
		free(source_code);
		source_code=NULL;
		PyErr_SetString(PyExc_TypeError, "Invalid function code");
		return NULL;
	}
	target_code=PyTuple_GetItem(((PyCodeObject*)def_code)->co_consts,0);
	if(!target_code)
	{
		Py_DECREF(def_code);
		free(source_code);
		source_code=NULL;
		PyErr_SetString(PyExc_TypeError, "Can not set function code");
		return NULL;
	}
	if(func_set_code(self,target_code,NULL)<0)
	{
		Py_DECREF(def_code);
		free(source_code);
		source_code=NULL;
		PyErr_SetString(PyExc_TypeError, "Can not set function code");
		return NULL;
	}
	Py_DECREF(def_code);
	if(self->source_code)
	free(self->source_code);
	self->source_code=source_code;
	Py_INCREF(Py_None);
	return Py_None;
}

static PyObject*
DynaFunc_get(DynaFuncObject *self)
{
	if(self->source_code)
	return PyUnicode_FromString(self->source_code);
	else
	{
		Py_INCREF(Py_None);
		return Py_None;
	}
}

static PyMethodDef DynaFunc_methods[] = {
	{"set", (PyCFunction) DynaFunc_set, METH_O,
	 PyDoc_STR("Set function code")},
	{"get", (PyCFunction) DynaFunc_get, METH_NOARGS,
	PyDoc_STR("get function code")},
	{NULL},
};

static int DynaFunc_traverse(DynaFuncObject *op, visitproc visit, void *arg)
{
	Py_TYPE(op)->tp_base->tp_traverse((PyFunctionObject*)op,visit,arg);
	return 0;
}

static void
DynaFunc_dealloc(DynaFuncObject *op)
{
	Py_TYPE(op)->tp_base->tp_dealloc((PyFunctionObject*)op);
}

static PyTypeObject DynaFuncType = {
	PyVarObject_HEAD_INIT(NULL, 0)
	.tp_name = "dynafunc.DynaFunc",
	.tp_doc = "Dynamic function objects",
	.tp_basicsize = sizeof(DynaFuncObject),
	.tp_itemsize = 0,
	.tp_flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_HAVE_GC,
	.tp_dealloc = (destructor)DynaFunc_dealloc,
	.tp_init = 0,
	.tp_new = DynaFunc_new,
	.tp_traverse = (traverseproc)DynaFunc_traverse,
	.tp_methods = DynaFunc_methods,
};

static void func_copy(PyFunctionObject *dst,PyFunctionObject *src)
{
	Py_XINCREF(src->func_code);		
	Py_XINCREF(src->func_globals);	 
	Py_XINCREF(src->func_defaults);	
	Py_XINCREF(src->func_kwdefaults);  
	Py_XINCREF(src->func_closure);	 
	Py_XINCREF(src->func_doc);		 
	Py_XINCREF(src->func_name);		
	Py_XINCREF(src->func_dict);		
	Py_XINCREF(src->func_weakreflist);
	Py_XINCREF(src->func_module);	  
	Py_XINCREF(src->func_annotations); 
	Py_XINCREF(src->func_qualname);	
	Py_XINCREF(src->ob_base.ob_type);
	*dst=*src;
	dst->ob_base.ob_refcnt=1;
}

static PyObject* DynaFunc_new_impl(PyFunctionObject *function_op)
{
	DynaFuncObject *dynafunc_op;
	dynafunc_op = PyObject_GC_New(DynaFuncObject, &DynaFuncType);
	if(!dynafunc_op)
	{
		PyErr_SetString(PyExc_TypeError, "Fail to construct the Dynamic Function object");
		return NULL;
	}
	func_copy(&(dynafunc_op->list),function_op);
	//dynafunc_op->list=*function_op;
	dynafunc_op->list.ob_base.ob_type=&DynaFuncType;
	dynafunc_op->source_code=NULL;
	PyObject_GC_Track(dynafunc_op);
	return dynafunc_op;
}

static PyObject *
DynaFunc_new(PyTypeObject *type, PyObject *args, PyObject *kwargs)
{
	PyObject *return_value = NULL;
	PyObject *object;
	PyCodeObject *code;
	PyObject *globals;
	PyObject *newargs;
	PyFunctionObject *function_op;
	Py_ssize_t len = (args != NULL) ? PyTuple_GET_SIZE(args) : 0;

	if (len!=1) {
		const char *msg = "DynaFunc() expected 1 arguments, got %zd";
		PyErr_Format(PyExc_TypeError, msg, len);
		return return_value;
	}
	PyArg_ParseTuple(args, "O", &object);
	if(PyFunction_Check(object))
	{
		function_op=(PyFunctionObject *)object;
	}
	else
	{
		_PyArg_BadArgument("DynaFunc", "argument 'code'", "function", object);
		return return_value;
	}
	return DynaFunc_new_impl(function_op);
}

void init_sandbox()
{
	struct sock_filter filter[]={
		BPF_STMT(BPF_LD+BPF_W+BPF_ABS, 4),
		BPF_JUMP(BPF_JMP+BPF_JEQ, 0xc000003e, 0, 5),
		BPF_STMT(BPF_LD+BPF_W+BPF_ABS,0),
		BPF_JUMP(BPF_JMP+BPF_JSET, 0x40000000, 3, 0),
		BPF_JUMP(BPF_JMP+BPF_JEQ,59,2,0),
		BPF_JUMP(BPF_JMP+BPF_JEQ,322,1,0),
		BPF_STMT(BPF_RET+BPF_K,SECCOMP_RET_ALLOW),
		BPF_STMT(BPF_RET+BPF_K,SECCOMP_RET_KILL),
	};
	struct sock_fprog prog = {								   
		(unsigned short)(sizeof(filter)/sizeof(filter[0])),
		filter
	};
	prctl(PR_SET_NO_NEW_PRIVS,1,0,0,0);
	prctl(PR_SET_SECCOMP,SECCOMP_MODE_FILTER,&prog);
}


static PyModuleDef DynaFuncModule = {
	PyModuleDef_HEAD_INIT,
	.m_name = "DynaFunc",
	.m_doc = "Module that creates an extension function type.",
	.m_size = -1,
};

PyMODINIT_FUNC
PyInit_DynaFunc(void)
{
	PyObject *m;
	DynaFuncType.tp_base = &PyFunction_Type;
	if (PyType_Ready(&DynaFuncType) < 0)
		return NULL;
	m = PyModule_Create(&DynaFuncModule);
	if (m == NULL)
		return NULL;
	Py_INCREF(&DynaFuncType);
	if (PyModule_AddObject(m, "DynaFunc", (PyObject *) &DynaFuncType) < 0)
	{
		Py_DECREF(&DynaFuncType);
		Py_DECREF(m);
		return NULL;
	}
	init_sandbox();
	return m;
}