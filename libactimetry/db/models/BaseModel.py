from opentera.db.Base import BaseMixin
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

class ActimetryBaseMixin(BaseMixin):

    @classmethod
    def get_by_id(cls, id_obj: int):
        id_field = cls.get_primary_key_name()
        data = cls.query_with_filters({id_field: id_obj})
        if data:
            return data[0]
        return None

    @classmethod
    def get_by_name(cls, name: str):
        name_field = cls.get_model_name() + '_name'
        data = cls.query_with_filters({name_field: name})
        if data:
            return data[0]
        return None

    @classmethod
    def update(cls, update_id: int, values: dict):
        update_values = cls.clean_values(values)
        if len(update_values) != len(values):
            raise SQLAlchemyError('Invalid values passed to update')

        if cls.get_primary_key_name() in update_values and update_id != update_values[cls.get_primary_key_name()]:
            raise SQLAlchemyError(f'Primary key cannot be updated ({cls.get_primary_key_name()})')

        # with Session(cls.db().engine) as session:
        update_obj = cls.db().session.query(cls).filter(getattr(cls, cls.get_primary_key_name()) == update_id).first()
        if update_obj is None:
            raise SQLAlchemyError(f'Update with invalid id : {update_id}')

        update_obj.from_json(update_values)
        cls.db().session.commit()

    @classmethod
    def delete(cls, id_todel, autocommit: bool = True):
        delete_obj = cls.db().session.query(cls).filter(getattr(cls, cls.get_primary_key_name()) == id_todel).first()
        if delete_obj is None:
            raise SQLAlchemyError(f'Delete with invalid id : {id_todel}')

        cannot_be_deleted_exception = delete_obj.delete_check_integrity()
        if cannot_be_deleted_exception:
            raise cannot_be_deleted_exception
        if delete_obj:
            if getattr(delete_obj, 'soft_delete', None):
                delete_obj.soft_delete()
            else:
                cls.db().session.delete(delete_obj)
            if autocommit:
                cls.commit()

    @classmethod
    def get_json_schema(cls) -> dict:
        from marshmallow_sqlalchemy import SQLAlchemyAutoSchema
        from marshmallow_jsonschema import JSONSchema


        class ModelSchema(SQLAlchemyAutoSchema):
            class Meta:
                model = cls
                load_instance = True
                # ordered
                ordered = True

                def get_exclusion_fields(cls):
                    exclude = ()
                    if hasattr(cls, 'deleted_at'):
                        exclude += ('deleted_at',)
                    if hasattr(cls, 'version_id'):
                        exclude += ('version_id',)
                    return exclude

                # Add fields to exclude
                exclude = get_exclusion_fields(cls)

        full_schema = JSONSchema().dump(ModelSchema())

        # Get model prefix (name)
        model_name = cls.get_model_name()

        # Empty schema that will be filled with the model columns information
        json_schema_model = {'type': 'object', 'properties': {}, 'required': []}

        # Get only the properties from the full schema
        for prop_name, prop_value in full_schema['definitions'][ModelSchema.__name__]['properties'].items():
            json_schema_model['properties'][prop_name] = prop_value

        # Set required fields to the primary key column
        json_schema_model['required'] = [cls.get_primary_key_name()]


        #Add required properties
        json_schema = {
            "type": "object",
            "properties": {
                model_name: json_schema_model
            },
            "required": [model_name]
        }
        return json_schema

# Declarative base, inherit from Base for all models
BaseModel = declarative_base(cls=ActimetryBaseMixin)
