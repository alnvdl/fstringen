from fstringen import gen, Model

model = Model.fromDict({
    "structs": {
        "mystruct": {
            "color": "string"
        },
        "anotherstruct": {
            "name": "string",
            "age": "int"
        }
    }
})


@gen()
def gen_struct(struct):
    fields = ["{} {}".format(field.name, field)
              for field in struct.select("*")]

    return f"""*
    type {struct.name} struct {{
        {fields}
    }}

    *"""


@gen(model=model, fname="myfile.go", comment="//")
def gen_myfile(model):
    return f"""*
    package main

    // Let's generate some structs!
    {[gen_struct(struct) for struct in model.select("/structs/*")]}
    *"""
