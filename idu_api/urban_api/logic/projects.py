import abc
from datetime import date
from typing import Any, Literal, Protocol

from otteroad import KafkaProducerClient

from idu_api.urban_api.dto import (
    FunctionalZoneDTO,
    FunctionalZoneSourceDTO,
    HexagonWithIndicatorsDTO,
    PageDTO,
    ProjectDTO,
    ProjectPhasesDTO,
    ProjectTerritoryDTO,
    ProjectWithTerritoryDTO,
    ScenarioBufferDTO,
    ScenarioDTO,
    ScenarioFunctionalZoneDTO,
    ScenarioGeometryDTO,
    ScenarioGeometryWithAllObjectsDTO,
    ScenarioIndicatorValueDTO,
    ScenarioPhysicalObjectDTO,
    ScenarioPhysicalObjectWithGeometryDTO,
    ScenarioServiceDTO,
    ScenarioServiceWithGeometryDTO,
    ScenarioUrbanObjectDTO,
    UserDTO,
)
from idu_api.urban_api.logic.physical_objects import Geom
from idu_api.urban_api.minio.services import ProjectStorageManager
from idu_api.urban_api.schemas import (
    ObjectGeometryPatch,
    ObjectGeometryPut,
    PhysicalObjectPatch,
    PhysicalObjectPut,
    PhysicalObjectWithGeometryPost,
    ProjectPatch,
    ProjectPhasesPut,
    ProjectPost,
    ProjectPut,
    ScenarioBufferDelete,
    ScenarioBufferPut,
    ScenarioBuildingPatch,
    ScenarioBuildingPost,
    ScenarioBuildingPut,
    ScenarioFunctionalZonePatch,
    ScenarioFunctionalZonePost,
    ScenarioFunctionalZonePut,
    ScenarioIndicatorValuePatch,
    ScenarioIndicatorValuePost,
    ScenarioIndicatorValuePut,
    ScenarioPatch,
    ScenarioPost,
    ScenarioPut,
    ScenarioServicePost,
    ServicePatch,
    ServicePut,
)


class UserProjectService(Protocol):  # pylint: disable=too-many-public-methods
    """Service to manipulate projects objects."""

    @abc.abstractmethod
    async def get_project_by_id(self, project_id: int, user: UserDTO | None) -> ProjectDTO:
        """Get project object by id."""

    @abc.abstractmethod
    async def get_project_territory_by_id(self, project_id: int, user: UserDTO | None) -> ProjectTerritoryDTO:
        """Get project territory object by id."""

    @abc.abstractmethod
    async def get_projects(
        self,
        user: UserDTO | None,
        only_own: bool,
        is_regional: bool,
        project_type: Literal["common", "city"] | None,
        territory_id: int | None,
        name: str | None,
        created_at: date | None,
        order_by: Literal["created_at", "updated_at"] | None,
        ordering: Literal["asc", "desc"] | None,
        paginate: bool = False,
    ) -> PageDTO[ProjectDTO]:
        """Get all public and user's projects."""

    async def get_all_projects(self) -> list[ProjectDTO]:
        """Get all projects minimal info."""

    @abc.abstractmethod
    async def get_projects_territories(
        self,
        user: UserDTO | None,
        only_own: bool,
        project_type: Literal["common", "city"] | None,
        territory_id: int | None,
    ) -> list[ProjectWithTerritoryDTO]:
        """Get all public and user's projects territories."""

    @abc.abstractmethod
    async def add_project(
        self,
        project: ProjectPost,
        user: UserDTO,
        kafka_producer: KafkaProducerClient,
        project_storage_manager: ProjectStorageManager,
    ) -> ProjectDTO:
        """Create project object."""

    @abc.abstractmethod
    async def create_base_scenario(
        self,
        project_id: int,
        scenario_id: int,
        kafka_producer: KafkaProducerClient,
    ) -> ScenarioDTO:
        """Create base scenario for given project from regional scenario."""

    @abc.abstractmethod
    async def put_project(self, project: ProjectPut, project_id: int, user: UserDTO) -> ProjectDTO:
        """Update project object by all its attributes."""

    @abc.abstractmethod
    async def patch_project(self, project: ProjectPatch, project_id: int, user: UserDTO) -> ProjectDTO:
        """Update project object by only given attributes."""

    @abc.abstractmethod
    async def delete_project(
        self,
        project_id: int,
        project_storage_manager: ProjectStorageManager,
        user: UserDTO,
    ) -> dict:
        """Delete project object."""

    @abc.abstractmethod
    async def get_scenarios(
        self,
        parent_id: int | None,
        project_id: int | None,
        territory_id: int | None,
        is_based: bool,
        only_own: bool,
        user: UserDTO | None,
    ) -> list[ScenarioDTO]:
        """Get list of scenario objects."""

    @abc.abstractmethod
    async def get_scenarios_by_project_id(self, project_id: int, user: UserDTO | None) -> list[ScenarioDTO]:
        """Get list of scenario objects by project id."""

    @abc.abstractmethod
    async def get_scenario_by_id(self, scenario_id: int, user: UserDTO | None) -> ScenarioDTO:
        """Get scenario object by id."""

    @abc.abstractmethod
    async def add_scenario(self, scenario: ScenarioPost, user: UserDTO) -> ScenarioDTO:
        """Create scenario object from base scenario."""

    @abc.abstractmethod
    async def copy_scenario(self, scenario: ScenarioPost, scenario_id: int, user: UserDTO) -> ScenarioDTO:
        """Create a new scenario from another scenario (copy) by its identifier."""

    @abc.abstractmethod
    async def put_scenario(self, scenario: ScenarioPut, scenario_id: int, user: UserDTO) -> ScenarioDTO:
        """Put project object."""

    @abc.abstractmethod
    async def patch_scenario(self, scenario: ScenarioPatch, scenario_id: int, user: UserDTO) -> ScenarioDTO:
        """Patch project object."""

    @abc.abstractmethod
    async def delete_scenario(self, scenario_id: int, user: UserDTO) -> dict:
        """Delete scenario object."""

    @abc.abstractmethod
    async def get_physical_objects_by_scenario_id(
        self,
        scenario_id: int,
        user: UserDTO | None,
        physical_object_type_id: int | None,
        physical_object_function_id: int | None,
    ) -> list[ScenarioPhysicalObjectDTO]:
        """Get list of physical objects by scenario identifier."""

    @abc.abstractmethod
    async def get_physical_objects_with_geometry_by_scenario_id(
        self,
        scenario_id: int,
        user: UserDTO | None,
        physical_object_type_id: int | None,
        physical_object_function_id: int | None,
    ) -> list[ScenarioPhysicalObjectWithGeometryDTO]:
        """Get list of physical objects with geometry by scenario identifier."""
    
    @abc.abstractmethod
    async def get_physical_objects_around_by_scenario_id(
        self,
        scenario_id: int,
        user: UserDTO | None,
        geometry: Geom,
        physical_object_type_id: int | None,
        buffer_meters: int
    ) -> list[ScenarioPhysicalObjectWithGeometryDTO]:
        """Get physical objects which are in buffer area of the given geometry."""

    @abc.abstractmethod
    async def get_context_physical_objects(
        self,
        scenario_id: int,
        user: UserDTO | None,
        physical_object_type_id: int | None,
        physical_object_function_id: int | None,
    ) -> list[ScenarioPhysicalObjectDTO]:
        """Get list of physical objects for 'context' of the project territory."""

    @abc.abstractmethod
    async def get_context_physical_objects_with_geometry(
        self,
        scenario_id: int,
        user: UserDTO | None,
        physical_object_type_id: int | None,
        physical_object_function_id: int | None,
    ) -> list[ScenarioPhysicalObjectWithGeometryDTO]:
        """Get list of physical objects with geometry for 'context' of the project territory."""

    @abc.abstractmethod
    async def add_physical_object_with_geometry(
        self,
        physical_object: PhysicalObjectWithGeometryPost,
        scenario_id: int,
        user: UserDTO,
    ) -> ScenarioUrbanObjectDTO:
        """Create scenario physical object with geometry."""

    @abc.abstractmethod
    async def update_physical_objects_by_function_id(
        self,
        physical_object: list[PhysicalObjectWithGeometryPost],
        scenario_id: int,
        user: UserDTO,
        physical_object_function_id: int,
    ) -> list[ScenarioUrbanObjectDTO]:
        """Delete all physical objects by physical object function identifier
        and upload new objects with the same function for given scenario."""

    @abc.abstractmethod
    async def put_physical_object(
        self,
        physical_object: PhysicalObjectPut,
        scenario_id: int,
        physical_object_id: int,
        is_scenario_object: bool,
        user: UserDTO,
    ) -> ScenarioPhysicalObjectDTO:
        """Update scenario physical object by all its attributes."""

    @abc.abstractmethod
    async def patch_physical_object(
        self,
        physical_object: PhysicalObjectPatch,
        scenario_id: int,
        physical_object_id: int,
        is_scenario_object: bool,
        user: UserDTO,
    ) -> ScenarioPhysicalObjectDTO:
        """Update scenario physical object by only given attributes."""

    @abc.abstractmethod
    async def delete_physical_object(
        self,
        scenario_id: int,
        physical_object_id: int,
        is_scenario_object: bool,
        user: UserDTO,
    ) -> dict:
        """Delete scenario physical object."""

    @abc.abstractmethod
    async def add_building(
        self,
        building: ScenarioBuildingPost,
        scenario_id: int,
        user: UserDTO,
    ) -> ScenarioPhysicalObjectDTO:
        """Add building to physical object for given scenario."""

    @abc.abstractmethod
    async def put_building(
        self,
        building: ScenarioBuildingPut,
        scenario_id: int,
        user: UserDTO,
    ) -> ScenarioPhysicalObjectDTO:
        """Add building to physical object or update existing one for given scenario."""

    @abc.abstractmethod
    async def patch_building(
        self,
        building: ScenarioBuildingPatch,
        scenario_id: int,
        building_id: int,
        is_scenario_object: bool,
        user: UserDTO,
    ) -> ScenarioPhysicalObjectDTO:
        """Update scenario building."""

    @abc.abstractmethod
    async def delete_building(
        self,
        scenario_id: int,
        building_id: int,
        is_scenario_object: bool,
        user: UserDTO,
    ) -> dict[str, str]:
        """Delete scenario building."""

    @abc.abstractmethod
    async def get_services_by_scenario_id(
        self,
        scenario_id: int,
        user: UserDTO | None,
        service_type_id: int | None,
        urban_function_id: int | None,
    ) -> list[ScenarioServiceDTO]:
        """Get list of services by scenario identifier."""

    @abc.abstractmethod
    async def get_services_with_geometry_by_scenario_id(
        self,
        scenario_id: int,
        user: UserDTO | None,
        service_type_id: int | None,
        urban_function_id: int | None,
    ) -> list[ScenarioServiceWithGeometryDTO]:
        """Get list of services with geometry by scenario identifier."""

    @abc.abstractmethod
    async def get_context_services(
        self,
        scenario_id: int,
        user: UserDTO | None,
        service_type_id: int | None,
        urban_function_id: int | None,
    ) -> list[ScenarioServiceDTO]:
        """Get list of services for 'context' of the project territory."""

    @abc.abstractmethod
    async def get_context_services_with_geometry(
        self,
        scenario_id: int,
        user: UserDTO | None,
        service_type_id: int | None,
        urban_function_id: int | None,
    ) -> list[ScenarioServiceWithGeometryDTO]:
        """Get list of services with geometry for 'context' of the project territory."""

    @abc.abstractmethod
    async def add_service(
        self, service: ScenarioServicePost, scenario_id: int, user: UserDTO
    ) -> ScenarioUrbanObjectDTO:
        """Create scenario service object."""

    @abc.abstractmethod
    async def put_service(
        self,
        service: ServicePut,
        scenario_id: int,
        service_id: int,
        is_scenario_object: bool,
        user: UserDTO,
    ) -> ScenarioServiceDTO:
        """Update scenario service by all its attributes."""

    @abc.abstractmethod
    async def patch_service(
        self,
        service: ServicePatch,
        scenario_id: int,
        service_id: int,
        is_scenario_object: bool,
        user: UserDTO,
    ) -> ScenarioServiceDTO:
        """Update scenario service by only given attributes."""

    @abc.abstractmethod
    async def delete_service(
        self,
        scenario_id: int,
        service_id: int,
        is_scenario_object: bool,
        user: UserDTO,
    ) -> dict:
        """Delete scenario service."""

    @abc.abstractmethod
    async def get_geometries_by_scenario_id(
        self,
        scenario_id: int,
        user: UserDTO | None,
        physical_object_id: int | None,
        service_id: int | None,
    ) -> list[ScenarioGeometryDTO]:
        """Get all geometries for given scenario."""

    @abc.abstractmethod
    async def get_geometries_with_all_objects_by_scenario_id(
        self,
        scenario_id: int,
        user: UserDTO | None,
        physical_object_type_id: int | None,
        service_type_id: int | None,
        physical_object_function_id: int | None,
        urban_function_id: int | None,
    ) -> list[ScenarioGeometryWithAllObjectsDTO]:
        """Get geometries with lists of physical objects and services by scenario identifier."""

    @abc.abstractmethod
    async def get_context_geometries(
        self,
        scenario_id: int,
        user: UserDTO | None,
        physical_object_id: int | None,
        service_id: int | None,
    ) -> list[ScenarioGeometryDTO]:
        """Get list of geometries for 'context' of the project territory."""

    @abc.abstractmethod
    async def get_context_geometries_with_all_objects(
        self,
        scenario_id: int,
        user: UserDTO | None,
        physical_object_type_id: int | None,
        service_type_id: int | None,
        physical_object_function_id: int | None,
        urban_function_id: int | None,
    ) -> list[ScenarioGeometryWithAllObjectsDTO]:
        """Get geometries with lists of physical objects and services for 'context' of the project territory."""

    @abc.abstractmethod
    async def put_object_geometry(
        self,
        object_geometry: ObjectGeometryPut,
        scenario_id: int,
        object_geometry_id: int,
        is_scenario_object: bool,
        user: UserDTO,
    ) -> ScenarioGeometryDTO:
        """Update scenario object geometry by all its attributes."""

    @abc.abstractmethod
    async def patch_object_geometry(
        self,
        object_geometry: ObjectGeometryPatch,
        scenario_id: int,
        object_geometry_id: int,
        is_scenario_object: bool,
        user: UserDTO,
    ) -> ScenarioGeometryDTO:
        """Update scenario object geometry by only given attributes."""

    @abc.abstractmethod
    async def delete_object_geometry(
        self,
        scenario_id: int,
        object_geometry_id: int,
        is_scenario_object: bool,
        user: UserDTO,
    ) -> dict:
        """Delete scenario object geometry."""

    @abc.abstractmethod
    async def get_scenario_indicators_values(
        self,
        scenario_id: int,
        indicator_ids: set[int] | None,
        indicator_group_id: int | None,
        territory_id: int | None,
        hexagon_id: int | None,
        user: UserDTO | None,
    ) -> list[ScenarioIndicatorValueDTO]:
        """Get project's indicators values for given scenario
        if relevant project is public or if you're the project owner."""

    @abc.abstractmethod
    async def add_scenario_indicator_value(
        self,
        indicator_value: ScenarioIndicatorValuePost,
        scenario_id: int,
        user: UserDTO,
        kafka_producer: KafkaProducerClient,
    ) -> ScenarioIndicatorValueDTO:
        """Add a new project's indicator value."""

    @abc.abstractmethod
    async def put_scenario_indicator_value(
        self,
        indicator_value: ScenarioIndicatorValuePut,
        scenario_id: int,
        user: UserDTO,
        kafka_producer: KafkaProducerClient,
    ) -> ScenarioIndicatorValueDTO:
        """Put project's indicator value."""

    @abc.abstractmethod
    async def patch_scenario_indicator_value(
        self,
        indicator_value: ScenarioIndicatorValuePatch,
        scenario_id: int,
        indicator_value_id: int,
        user: UserDTO,
        kafka_producer: KafkaProducerClient,
    ) -> ScenarioIndicatorValueDTO:
        """Patch project's indicator value."""

    @abc.abstractmethod
    async def delete_scenario_indicators_values_by_scenario_id(self, scenario_id: int, user: UserDTO) -> dict:
        """Delete all project's indicators values for given scenario if you're the project owner."""

    @abc.abstractmethod
    async def delete_scenario_indicator_value_by_id(
        self, scenario_id: int, indicator_value_id: int, user: UserDTO
    ) -> dict:
        """Delete specific project's indicator values by indicator value identifier if you're the project owner."""

    @abc.abstractmethod
    async def get_hexagons_with_indicators_by_scenario_id(
        self,
        scenario_id: int,
        indicator_ids: set[int] | None,
        indicators_group_id: int | None,
        user: UserDTO | None,
    ) -> list[HexagonWithIndicatorsDTO]:
        """Get project's indicators values for given regional scenario with hexagons."""

    @abc.abstractmethod
    async def update_all_indicators_values_by_scenario_id(self, scenario_id: int, user: UserDTO) -> dict[str, Any]:
        """Update all indicators values for given scenario."""

    @abc.abstractmethod
    async def get_functional_zones_sources_by_scenario_id(
        self, scenario_id: int, user: UserDTO | None
    ) -> list[FunctionalZoneSourceDTO]:
        """Get list of pairs year + source for functional zones for given scenario."""

    @abc.abstractmethod
    async def get_functional_zones_by_scenario_id(
        self,
        scenario_id: int,
        year: int,
        source: str,
        functional_zone_type_id: int | None,
        user: UserDTO | None,
    ) -> list[ScenarioFunctionalZoneDTO]:
        """Get list of functional zone objects by scenario identifier."""

    @abc.abstractmethod
    async def get_context_functional_zones_sources(
        self, scenario_id: int, user: UserDTO | None
    ) -> list[FunctionalZoneSourceDTO]:
        """Get list of pairs year + source for functional zones for 'context' of the project territory."""

    @abc.abstractmethod
    async def get_context_functional_zones(
        self,
        scenario_id: int,
        year: int,
        source: str,
        functional_zone_type_id: int | None,
        user: UserDTO | None,
    ) -> list[FunctionalZoneDTO]:
        """Get list of functional zone objects for 'context' of the project territory."""

    @abc.abstractmethod
    async def add_scenario_functional_zones(
        self, profiles: list[ScenarioFunctionalZonePost], scenario_id: int, user: UserDTO
    ) -> list[ScenarioFunctionalZoneDTO]:
        """Add list of scenario functional zone objects."""

    @abc.abstractmethod
    async def put_scenario_functional_zone(
        self,
        profile: ScenarioFunctionalZonePut,
        scenario_id: int,
        functional_zone_id: int,
        user: UserDTO,
    ) -> ScenarioFunctionalZoneDTO:
        """Update scenario functional zone object by all its attributes."""

    @abc.abstractmethod
    async def patch_scenario_functional_zone(
        self,
        profile: ScenarioFunctionalZonePatch,
        scenario_id: int,
        functional_zone_id: int,
        user: UserDTO,
    ) -> ScenarioFunctionalZoneDTO:
        """Update scenario functional zone object by only given attributes."""

    @abc.abstractmethod
    async def delete_functional_zones_by_scenario_id(self, scenario_id: int, user: UserDTO) -> dict:
        """Delete functional zones by scenario identifier."""

    @abc.abstractmethod
    async def get_project_phases_by_id(self, project_id: int, user: UserDTO | None) -> ProjectPhasesDTO:
        """Get project's phases by project identifier."""

    @abc.abstractmethod
    async def put_project_phases(
        self, project_id: int, project_phases: ProjectPhasesPut, user: UserDTO | None
    ) -> ProjectPhasesDTO:
        """Put project's phases."""

    @abc.abstractmethod
    async def get_buffers_by_scenario_id(
        self,
        scenario_id: int,
        buffer_type_id: int | None,
        physical_object_type_id: int | None,
        service_type_id: int | None,
        user: UserDTO | None,
    ) -> list[ScenarioBufferDTO]:
        """Get list of buffers by scenario identifier."""

    @abc.abstractmethod
    async def get_context_buffers(
        self,
        scenario_id: int,
        buffer_type_id: int | None,
        physical_object_type_id: int | None,
        service_type_id: int | None,
        user: UserDTO | None,
    ) -> list[ScenarioBufferDTO]:
        """Get list of buffers for 'context' of the project territory."""

    @abc.abstractmethod
    async def put_scenario_buffer(
        self,
        buffer: ScenarioBufferPut,
        scenario_id: int,
        user: UserDTO | None,
    ) -> ScenarioBufferDTO:
        """Get buffer objects by scenario identifier."""

    @abc.abstractmethod
    async def delete_scenario_buffer(
        self,
        buffer: ScenarioBufferDelete,
        scenario_id: int,
        user: UserDTO | None,
    ) -> dict:
        """Get buffer objects by scenario identifier."""
