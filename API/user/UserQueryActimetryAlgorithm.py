from flask_babel import gettext
from flask_restx import Resource, inputs
from FlaskModule import user_api_ns as api
from opentera.services.ServiceAccessManager import (
    ServiceAccessManager,
    current_login_type,
    LoginType,
)
from libopenimu.algorithms.BaseAlgorithm import BaseAlgorithmFactory

# Parser definition(s)
get_parser = api.parser()
get_parser.add_argument(
    "key", type=str, help="Unique key (identifier) of the processing algorithm to query"
)
get_parser.add_argument(
    "list",
    type=inputs.boolean,
    help="Flag that limits the returned data to minimal information",
)


class UserQueryActimetryAlgorithm(Resource):

    def __init__(self, _api, *args, **kwargs):
        Resource.__init__(self, _api, *args, **kwargs)
        self.module = kwargs.get("flaskModule", None)
        self.test = kwargs.get("test", False)

    @api.doc(
        description="Get available processing algorithms or details about a specific one. If no algorithm key is "
        "specified, returns all available processing algorithms.",
        responses={
            200: "Success - returns list of algorithms.",
            403: "Forbidden access",
            404: "Not found",
            500: "Database error",
        },
    )
    @api.expect(get_parser)
    @ServiceAccessManager.token_required(
        allow_static_tokens=False, allow_dynamic_tokens=True
    )
    def get(self):
        """
        Get processing algorithms information
        """
        if current_login_type != LoginType.USER_LOGIN:
            return gettext("Invalid login type"), 403

        args = get_parser.parse_args()

        algos = []

        # List available factories / algorithms from libopenimu
        for factory in BaseAlgorithmFactory.factories:
            factory_info = factory.info()
            factory_info["parameters"] = factory.params()
            factory_info["results"] = factory.results()
            algos.append(factory_info)

        # TODO: Query libopenimu for available algorithms
        # For now, "test" mode with static infos
        # algos = [
        #     {
        #         "key": "evenson2008",
        #         "name": "Evenson 2008",
        #         "author": "Simon Briere",
        #         "version": 0.1,
        #         "description": """\
        #           Classify activity counts into various intensity levels (Sedentary, Light, Moderate, Vigorous)
        #           using 3D accelerometer data.

        #           A band-filter is applied to raw accelerometers data with a frequency response of 0.25 to 2.5 Hz.

        #           Each digitized signal is summed over a user specified time interval (epoch), and at the end of each epoch
        #           the activity count is stored internally and the accumulator is reset to zero.

        #           Epoch sizes of 15s are used, and activity counts are expressed as the average counts per epoch.

        #           Notes:
        #           - Uses all 3 accelerometers axis
        #           - Epoch size = 15 seconds
        #           - Final data is reported in seconds
        #           """,
        #         "parameters": [
        #             {
        #                 "name": "sedentary_cutoff",
        #                 "description": "Cut-off Sedentary (15s)",
        #             },
        #             {"name": "light_cutoff", "description": "Cut-off Light (15s)"},
        #             {
        #                 "name": "moderate_cutoff",
        #                 "description": "Cut-off Moderate (15s)",
        #             },
        #             {
        #                 "name": "vigorous_cutoff",
        #                 "description": "Cut-off Vigorous (15s)",
        #             },
        #         ],
        #         "results": [
        #             {
        #                 "name": "sedentary_time",
        #                 "description": "Sedentary Activity Time (minutes)",
        #             },
        #             {
        #                 "name": "light_time",
        #                 "description": "Light Activity Time (minutes)",
        #             },
        #             {
        #                 "name": "moderate_time",
        #                 "description": "Moderate Activity Time (minutes)",
        #             },
        #             {
        #                 "name": "vigorous_time",
        #                 "description": "Vigorous Activity Time (minutes)",
        #             },
        #         ],
        #     },
        #     {
        #         "key": "freedson1998",
        #         "name": "Freedson 1998",
        #         "author": "Dominic Létourneau",
        #         "version": 0.1,
        #         "description": """\
        #             It is a uniaxial accelerometer that assesses accelerations ranging from 0.05-2.0 G and is band limited with a
        #             frequency response from 0.25-2.5 Hz.

        #             The acceleration signal is filtered by an analog bandpass filter and digitized by an 8 bit A/D converter at a
        #             sampling rate of 10 samples per second.

        #             Each digitized signal is summed over a user specified time interval (epoch), and at the end of each epoch
        #             the activity count is stored internally and the accumulator is reset to zero. In the current study, a 60-s
        #              epoch was used and activity counts were expressed as the average counts per minute over the 6 min of exercise.

        #             Cut points (intensity buckets):
        #             * https://actigraph.desk.com/customer/portal/articles/2515802

        #             Counts (accelerator sum over 60 s)
        #             * https://actigraph.desk.com/customer/portal/articles/2515580-What-are-counts-

        #             Notes:
        #             --> Only Y axis used on Actigraph devices.
        #             8 bits = 256 = 2g

        #             epoch = 60 seconds
        #                   """,
        #         "parameters": [
        #             {
        #                 "name": "sedentary_cutoff",
        #                 "description": "Cut-off Sedentary (15s)",
        #             },
        #             {"name": "light_cutoff", "description": "Cut-off Light (15s)"},
        #             {
        #                 "name": "moderate_cutoff",
        #                 "description": "Cut-off Moderate (15s)",
        #             },
        #             {
        #                 "name": "vigorous_cutoff",
        #                 "description": "Cut-off Vigorous (15s)",
        #             },
        #         ],
        #         "results": [
        #             {
        #                 "name": "sedentary_time",
        #                 "description": "Sedentary Activity Time (minutes)",
        #             },
        #             {
        #                 "name": "light_time",
        #                 "description": "Light Activity Time (minutes)",
        #             },
        #             {
        #                 "name": "moderate_time",
        #                 "description": "Moderate Activity Time (minutes)",
        #             },
        #             {
        #                 "name": "vigorous_time",
        #                 "description": "Vigorous Activity Time (minutes)",
        #             },
        #         ],
        #     },
        # ]

        if args["key"]:
            if not args["key"] in [algo["key"] for algo in algos]:
                return gettext("Unknown processing algorithm"), 404

            return [algo for algo in algos if algo["key"] == args["key"]], 200

        # List all available processing algorithms
        if args["list"]:
            base_algos = [
                {"key": algo["key"], "name": algo["name"], "version": algo["version"]}
                for algo in algos
            ]
            return base_algos, 200

        return algos, 200
