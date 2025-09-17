"""Unit tests for physical object types are defined here."""

from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.sql import delete, select, update

from idu_api.common.db.entities import (
    object_service_types_dict,
    physical_object_functions_dict,
    physical_object_types_dict,
    service_types_dict,
    urban_functions_dict,
)
from idu_api.common.exceptions.logic.common import EntitiesNotFoundByIds, EntityAlreadyExists, EntityNotFoundById
from idu_api.urban_api.dto import (
    PhysicalObjectFunctionDTO,
    PhysicalObjectTypeDTO,
    PhysicalObjectTypesHierarchyDTO,
    ServiceTypeDTO,
)
from idu_api.urban_api.logic.impl.helpers.physical_object_types import (
    add_physical_object_function_to_db,
    add_physical_object_type_to_db,
    delete_physical_object_function_from_db,
    delete_physical_object_type_from_db,
    get_physical_object_function_by_id_from_db,
    get_physical_object_functions_by_parent_id_from_db,
    get_physical_object_type_by_id_from_db,
    get_physical_object_types_from_db,
    get_physical_object_types_hierarchy_from_db,
    get_service_types_by_physical_object_type_id_from_db,
    patch_physical_object_function_to_db,
    patch_physical_object_type_to_db,
    put_physical_object_function_to_db,
)
from idu_api.urban_api.schemas import (
    PhysicalObjectFunction,
    PhysicalObjectFunctionPatch,
    PhysicalObjectFunctionPost,
    PhysicalObjectFunctionPut,
    PhysicalObjectType,
    PhysicalObjectTypePatch,
    PhysicalObjectTypePost,
    ServiceType,
)
from tests.urban_api.helpers.connection import MockConnection

####################################################################################
#                           Default use-case tests                                 #
####################################################################################


@pytest.mark.asyncio
async def test_get_physical_object_types_from_db(mock_conn: MockConnection):
    """Test the get_physical_object_types_from_db function."""

    # Arrange
    physical_object_function_id = 1
    name = "mock_string"
    statement = (
        select(physical_object_types_dict, physical_object_functions_dict.c.name.label("physical_object_function_name"))
        .select_from(
            physical_object_types_dict.join(
                physical_object_functions_dict,
                physical_object_functions_dict.c.physical_object_function_id
                == physical_object_types_dict.c.physical_object_function_id,
            )
        )
        .where(
            physical_object_types_dict.c.physical_object_function_id == physical_object_function_id,
            physical_object_types_dict.c.name.ilike(f"%{name}%"),
        )
        .order_by(physical_object_types_dict.c.physical_object_type_id)
    )

    # Act
    result = await get_physical_object_types_from_db(mock_conn, physical_object_function_id, name)

    # Assert
    assert isinstance(result, list), "Result should be a list."
    assert all(
        isinstance(item, PhysicalObjectTypeDTO) for item in result
    ), "Each item should be a PhysicalObjectTypeDTO."
    assert isinstance(
        PhysicalObjectType.from_dto(result[0]), PhysicalObjectType
    ), "Couldn't create pydantic model from DTO."
    mock_conn.execute_mock.assert_called_once_with(str(statement))


@pytest.mark.asyncio
async def test_get_physical_object_type_by_id_from_db(mock_conn: MockConnection):
    """Test the get_physical_object_type_by_id_from_db function."""

    # Arrange
    physical_object_type_id = 1
    statement = (
        select(physical_object_types_dict, physical_object_functions_dict.c.name.label("physical_object_function_name"))
        .select_from(
            physical_object_types_dict.join(
                physical_object_functions_dict,
                physical_object_functions_dict.c.physical_object_function_id
                == physical_object_types_dict.c.physical_object_function_id,
            )
        )
        .where(physical_object_types_dict.c.physical_object_type_id == physical_object_type_id)
    )

    # Act
    result = await get_physical_object_type_by_id_from_db(mock_conn, physical_object_type_id)

    # Assert
    assert isinstance(result, PhysicalObjectTypeDTO), "Result should be a PhysicalObjectTypeDTO."
    assert isinstance(
        PhysicalObjectType.from_dto(result), PhysicalObjectType
    ), "Couldn't create pydantic model from DTO."
    mock_conn.execute_mock.assert_called_once_with(str(statement))


@pytest.mark.asyncio
async def test_add_physical_object_type_to_db(
    mock_conn: MockConnection, physical_object_type_post_req: PhysicalObjectTypePost
):
    """Test the add_physical_object_type_to_db function."""

    # Arrange
    statement_insert = (
        insert(physical_object_types_dict)
        .values(**physical_object_type_post_req.model_dump())
        .returning(physical_object_types_dict.c.physical_object_type_id)
    )

    # Act
    result = await add_physical_object_type_to_db(mock_conn, physical_object_type_post_req)

    # Assert
    assert isinstance(result, PhysicalObjectTypeDTO), "Result should be a PhysicalObjectTypeDTO."
    assert isinstance(
        PhysicalObjectType.from_dto(result), PhysicalObjectType
    ), "Couldn't create pydantic model from DTO."
    mock_conn.execute_mock.assert_any_call(str(statement_insert))
    mock_conn.commit_mock.assert_called_once()


@pytest.mark.asyncio
async def test_patch_physical_object_type_to_db(
    mock_conn: MockConnection, physical_object_type_patch_req: PhysicalObjectTypePatch
):
    """Test the patch_physical_object_type_to_db function."""

    # Arrange
    physical_object_type_id = 1
    statement_update = (
        update(physical_object_types_dict)
        .where(physical_object_types_dict.c.physical_object_type_id == physical_object_type_id)
        .values(**physical_object_type_patch_req.model_dump(exclude_unset=True))
    )

    # Act
    result = await patch_physical_object_type_to_db(mock_conn, physical_object_type_id, physical_object_type_patch_req)

    # Assert
    assert isinstance(result, PhysicalObjectTypeDTO), "Result should be a PhysicalObjectTypeDTO."
    assert isinstance(
        PhysicalObjectType.from_dto(result), PhysicalObjectType
    ), "Couldn't create pydantic model from DTO."
    mock_conn.execute_mock.assert_any_call(str(statement_update))
    mock_conn.commit_mock.assert_called_once()


@pytest.mark.asyncio
async def test_delete_physical_object_type_from_db(mock_conn: MockConnection):
    """Test the delete_physical_object_type_from_db function."""

    # Arrange
    physical_object_type_id = 1
    statement = delete(physical_object_types_dict).where(
        physical_object_types_dict.c.physical_object_type_id == physical_object_type_id
    )

    # Act
    with patch("idu_api.urban_api.logic.impl.helpers.physical_object_types.check_existence") as mock_check_existence:
        result = await delete_physical_object_type_from_db(mock_conn, physical_object_type_id)
        mock_check_existence.return_value = False
        with pytest.raises(EntityNotFoundById):
            await delete_physical_object_type_from_db(mock_conn, physical_object_type_id)

    # Assert
    assert result == {"status": "ok"}, "Result should be {'status': 'ok'}."
    mock_conn.execute_mock.assert_called_once_with(str(statement))
    mock_conn.commit_mock.assert_called_once()


@pytest.mark.asyncio
async def test_get_physical_object_functions_by_parent_id_from_db(mock_conn: MockConnection):
    """Test the get_physical_object_functions_by_parent_id_from_db function."""

    # Arrange
    parent_id = 1
    name = "mock_string"
    physical_object_functions_parents = physical_object_functions_dict.alias("physical_object_functions_parents")
    statement = select(
        physical_object_functions_dict, physical_object_functions_parents.c.name.label("parent_name")
    ).select_from(
        physical_object_functions_dict.outerjoin(
            physical_object_functions_parents,
            physical_object_functions_parents.c.physical_object_function_id
            == physical_object_functions_dict.c.parent_id,
        )
    )
    cte_statement = statement.where(physical_object_functions_dict.c.parent_id == parent_id)
    cte_statement = cte_statement.cte(name="physical_object_function_recursive", recursive=True)
    recursive_part = statement.join(
        cte_statement, physical_object_functions_dict.c.parent_id == cte_statement.c.physical_object_function_id
    )
    recursive_statement = select(cte_statement.union_all(recursive_part))
    statement = statement.where(physical_object_functions_dict.c.parent_id == parent_id)
    requested_physical_object_functions = statement.cte("requested_physical_object_functions")
    statement = select(requested_physical_object_functions)
    recursive_statement = select(recursive_statement.cte("requested_physical_object_functions"))
    statement_with_filters = statement.where(requested_physical_object_functions.c.name.ilike(f"%{name}%"))

    # Act
    await get_physical_object_functions_by_parent_id_from_db(mock_conn, parent_id, None, True)
    await get_physical_object_functions_by_parent_id_from_db(mock_conn, parent_id, name, False)
    with patch("idu_api.urban_api.logic.impl.helpers.physical_object_types.check_existence") as mock_check_existence:
        result = await get_physical_object_functions_by_parent_id_from_db(mock_conn, parent_id, None, False)
        mock_check_existence.return_value = False
        with pytest.raises(EntityNotFoundById):
            await get_physical_object_functions_by_parent_id_from_db(mock_conn, parent_id, None, False)

    # Assert
    assert isinstance(result, list), "Result should be a list."
    assert all(
        isinstance(item, PhysicalObjectFunctionDTO) for item in result
    ), "Each item should be a PhysicalObjectFunctionDTO."
    assert isinstance(
        PhysicalObjectFunction.from_dto(result[0]), PhysicalObjectFunction
    ), "Couldn't create pydantic model from DTO."
    mock_conn.execute_mock.assert_any_call(str(statement))
    mock_conn.execute_mock.assert_any_call(str(recursive_statement))
    mock_conn.execute_mock.assert_any_call(str(statement_with_filters))


@pytest.mark.asyncio
async def test_get_physical_object_function_by_id_from_db(mock_conn: MockConnection):
    """Test the get_physical_object_function_by_id_from_db function."""

    # Arrange
    physical_object_function_id = 1
    physical_object_functions_parents = physical_object_functions_dict.alias("physical_object_functions_parents")
    statement = (
        select(physical_object_functions_dict, physical_object_functions_parents.c.name.label("parent_name"))
        .select_from(
            physical_object_functions_dict.outerjoin(
                physical_object_functions_parents,
                physical_object_functions_parents.c.physical_object_function_id
                == physical_object_functions_dict.c.parent_id,
            )
        )
        .where(physical_object_functions_dict.c.physical_object_function_id == physical_object_function_id)
    )

    # Act
    result = await get_physical_object_function_by_id_from_db(mock_conn, physical_object_function_id)

    # Assert
    assert isinstance(result, PhysicalObjectFunctionDTO), "Result should be a PhysicalObjectFunctionDTO."
    assert isinstance(
        PhysicalObjectFunction.from_dto(result), PhysicalObjectFunction
    ), "Couldn't create pydantic model from DTO."
    mock_conn.execute_mock.assert_called_once_with(str(statement))


@pytest.mark.asyncio
async def test_add_physical_object_function_to_db(
    mock_conn: MockConnection, physical_object_function_post_req: PhysicalObjectFunctionPost
):
    """Test the add_physical_object_function_to_db function."""

    # Arrange
    statement = (
        insert(physical_object_functions_dict)
        .values(**physical_object_function_post_req.model_dump())
        .returning(physical_object_functions_dict.c.physical_object_function_id)
    )

    # Act
    result = await add_physical_object_function_to_db(mock_conn, physical_object_function_post_req)

    # Assert
    assert isinstance(result, PhysicalObjectFunctionDTO), "Result should be a PhysicalObjectFunctionDTO."
    assert isinstance(
        PhysicalObjectFunction.from_dto(result), PhysicalObjectFunction
    ), "Couldn't create pydantic model from DTO."
    mock_conn.execute_mock.assert_any_call(str(statement))
    mock_conn.commit_mock.assert_called_once()


@pytest.mark.asyncio
async def test_put_physical_object_function_to_db(
    mock_conn: MockConnection, physical_object_function_put_req: PhysicalObjectFunctionPut
):
    """Test the put_physical_object_function_to_db function."""

    # Arrange
    statement = (
        insert(physical_object_functions_dict)
        .values(**physical_object_function_put_req.model_dump())
        .on_conflict_do_update(
            index_elements=["name"],
            set_=physical_object_function_put_req.model_dump(),
        )
        .returning(physical_object_functions_dict.c.physical_object_function_id)
    )

    # Act
    result = await put_physical_object_function_to_db(mock_conn, physical_object_function_put_req)

    # Assert
    assert isinstance(result, PhysicalObjectFunctionDTO), "Result should be a PhysicalObjectFunctionDTO."
    assert isinstance(
        PhysicalObjectFunction.from_dto(result), PhysicalObjectFunction
    ), "Couldn't create pydantic model from DTO."
    mock_conn.execute_mock.assert_any_call(str(statement))
    mock_conn.commit_mock.assert_called_once()


@pytest.mark.asyncio
async def test_patch_physical_object_function_to_db(
    mock_conn: MockConnection, physical_object_function_patch_req: PhysicalObjectFunctionPatch
):
    """Test the patch_physical_object_function_to_db function."""

    # Arrange
    physical_object_function_id = 1
    statement = (
        update(physical_object_functions_dict)
        .where(physical_object_functions_dict.c.physical_object_function_id == physical_object_function_id)
        .values(**physical_object_function_patch_req.model_dump(exclude_unset=True))
    )

    # Act
    result = await patch_physical_object_function_to_db(
        mock_conn, physical_object_function_id, physical_object_function_patch_req
    )

    # Assert
    assert isinstance(result, PhysicalObjectFunctionDTO), "Result should be a PhysicalObjectFunctionDTO."
    assert isinstance(
        PhysicalObjectFunction.from_dto(result), PhysicalObjectFunction
    ), "Couldn't create pydantic model from DTO."
    mock_conn.execute_mock.assert_any_call(str(statement))
    mock_conn.commit_mock.assert_called_once()


@pytest.mark.asyncio
async def test_delete_physical_object_function_from_db(mock_conn: MockConnection):
    """Test the delete_physical_object_function_from_db function."""

    # Arrange
    physical_object_function_id = 1
    statement = delete(physical_object_functions_dict).where(
        physical_object_functions_dict.c.physical_object_function_id == physical_object_function_id
    )

    # Act
    with patch("idu_api.urban_api.logic.impl.helpers.physical_object_types.check_existence") as mock_check_existence:
        result = await delete_physical_object_function_from_db(mock_conn, physical_object_function_id)
        mock_check_existence.return_value = False
        with pytest.raises(EntityNotFoundById):
            await delete_physical_object_function_from_db(mock_conn, physical_object_function_id)

    # Assert
    assert result == {"status": "ok"}, "Result should be {'status': 'ok'}."
    mock_conn.execute_mock.assert_called_once_with(str(statement))
    mock_conn.commit_mock.assert_called_once()


@pytest.mark.asyncio
async def test_get_physical_object_types_hierarchy_from_db(mock_conn: MockConnection):
    """Test the get_physical_object_types_hierarchy_from_db function."""

    # Arrange
    statement = (
        select(physical_object_types_dict, physical_object_functions_dict.c.name.label("physical_object_function_name"))
        .select_from(
            physical_object_types_dict.outerjoin(
                physical_object_functions_dict,
                physical_object_functions_dict.c.physical_object_function_id
                == physical_object_types_dict.c.physical_object_function_id,
            )
        )
        .order_by(physical_object_types_dict.c.physical_object_type_id)
    )

    # Act
    with pytest.raises(EntitiesNotFoundByIds):
        await get_physical_object_types_hierarchy_from_db(mock_conn, {1, 2})
    result = await get_physical_object_types_hierarchy_from_db(mock_conn, None)

    # Assert
    assert isinstance(result, list), "Result should be a list."
    assert all(
        isinstance(item, PhysicalObjectTypesHierarchyDTO) for item in result
    ), "Each item should be a PhysicalObjectTypesHierarchyDTO."
    mock_conn.execute_mock.assert_any_call(str(statement))


@pytest.mark.asyncio
async def test_get_service_types_by_physical_object_type_id_from_db(mock_conn: MockConnection):
    """Test the get_service_types_by_physical_object_type_id_from_db function."""

    # Arrange
    async def check_physical_object_type_id(conn, table, conditions, not_conditions=None):
        if table == physical_object_types_dict:
            return False
        return True

    physical_object_type_id = 1
    statement = (
        select(service_types_dict, urban_functions_dict.c.name.label("urban_function_name"))
        .select_from(
            service_types_dict.join(
                urban_functions_dict,
                urban_functions_dict.c.urban_function_id == service_types_dict.c.urban_function_id,
            ).join(
                object_service_types_dict,
                object_service_types_dict.c.service_type_id == service_types_dict.c.service_type_id,
            )
        )
        .where(object_service_types_dict.c.physical_object_type_id == physical_object_type_id)
        .order_by(service_types_dict.c.service_type_id)
    )

    # Act
    with patch(
        "idu_api.urban_api.logic.impl.helpers.physical_object_types.check_existence",
        new=AsyncMock(side_effect=check_physical_object_type_id),
    ):
        with pytest.raises(EntityNotFoundById):
            await get_service_types_by_physical_object_type_id_from_db(mock_conn, physical_object_type_id)
    result = await get_service_types_by_physical_object_type_id_from_db(mock_conn, physical_object_type_id)

    # Assert
    assert isinstance(result, list), "Result should be a list."
    assert all(isinstance(item, ServiceTypeDTO) for item in result), "Each item should be a ServiceTypeDTO."
    assert isinstance(ServiceType.from_dto(result[0]), ServiceType), "Couldn't create pydantic model from DTO."
    mock_conn.execute_mock.assert_called_with(str(statement))
