# -*- encoding: utf-8 -*-
#
# Copyright © 2020—2021 Mergify SAS
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from unittest import mock

import pytest

from mergify_engine import check_api
from mergify_engine import context
from mergify_engine import github_types
from mergify_engine import utils
from mergify_engine.dashboard import subscription


@pytest.mark.asyncio
async def test_summary_synchronization_cache(
    redis_cache: utils.RedisCache,
) -> None:
    gh_owner = github_types.GitHubAccount(
        {
            "login": github_types.GitHubLogin("user"),
            "id": github_types.GitHubAccountIdType(0),
            "type": "User",
            "avatar_url": "",
        }
    )

    gh_repo = github_types.GitHubRepository(
        {
            "archived": False,
            "url": "",
            "html_url": "",
            "default_branch": github_types.GitHubRefType(""),
            "id": github_types.GitHubRepositoryIdType(456),
            "full_name": "user/ref",
            "name": github_types.GitHubRepositoryName("name"),
            "private": False,
            "owner": gh_owner,
        }
    )
    installation_json = github_types.GitHubInstallation(
        {
            "id": github_types.GitHubInstallationIdType(12345),
            "target_type": gh_owner["type"],
            "permissions": {},
            "account": gh_owner,
        }
    )

    async def items(*args, **kwargs):
        if False:
            yield
        return

    async def post_check(*args, **kwargs):
        return mock.Mock(
            status_code=200,
            json=mock.Mock(
                return_value=github_types.GitHubCheckRun(
                    {
                        "head_sha": "ce587453ced02b1526dfb4cb910479d431683101",
                        "details_url": "https://example.com",
                        "status": "completed",
                        "conclusion": "neutral",
                        "name": "neutral",
                        "id": 1236,
                        "app": {
                            "id": 1234,
                            "name": "CI",
                            "owner": {
                                "type": "User",
                                "id": 1234,
                                "login": "goo",
                                "avatar_url": "https://example.com",
                            },
                        },
                        "external_id": "",
                        "pull_requests": [],
                        "before": "4eef79d038b0327a5e035fd65059e556a55c6aa4",
                        "after": "4eef79d038b0327a5e035fd65059e556a55c6aa4",
                        "started_at": "",
                        "completed_at": "",
                        "html_url": "https://example.com",
                        "check_suite": {"id": 1234},
                        "output": {
                            "summary": "",
                            "title": "It runs!",
                            "text": "",
                            "annotations": [],
                            "annotations_count": 0,
                            "annotations_url": "https://example.com",
                        },
                    }
                )
            ),
        )

    client = mock.AsyncMock()
    client.auth.get_access_token.return_value = "<token>"
    client.items = items
    client.post.side_effect = post_check

    sub = subscription.Subscription(
        redis_cache, 0, "", frozenset([subscription.Features.PUBLIC_REPOSITORY])
    )
    installation = context.Installation(
        installation_json,
        sub,
        client,
        redis_cache,
    )
    repository = context.Repository(installation, gh_repo)
    ctxt = await context.Context.create(
        repository,
        {
            "node_id": "42",
            "locked": False,
            "assignees": [],
            "requested_reviewers": [],
            "requested_teams": [],
            "milestone": None,
            "title": "",
            "body": "",
            "updated_at": github_types.ISODateTimeType("2021-06-01T18:41:39Z"),
            "created_at": github_types.ISODateTimeType("2021-06-01T18:41:39Z"),
            "closed_at": None,
            "id": github_types.GitHubPullRequestId(0),
            "maintainer_can_modify": False,
            "rebaseable": False,
            "draft": False,
            "merge_commit_sha": None,
            "labels": [],
            "number": github_types.GitHubPullRequestNumber(6),
            "commits": 1,
            "merged": True,
            "state": "closed",
            "changed_files": 1,
            "html_url": "<html_url>",
            "base": {
                "label": "",
                "sha": github_types.SHAType("sha"),
                "user": {
                    "login": github_types.GitHubLogin("user"),
                    "id": github_types.GitHubAccountIdType(0),
                    "type": "User",
                    "avatar_url": "",
                },
                "ref": github_types.GitHubRefType("ref"),
                "label": "",
                "repo": gh_repo,
            },
            "head": {
                "label": "",
                "sha": github_types.SHAType("old-sha-one"),
                "ref": github_types.GitHubRefType("fork"),
                "user": {
                    "login": github_types.GitHubLogin("user"),
                    "id": github_types.GitHubAccountIdType(0),
                    "type": "User",
                    "avatar_url": "",
                },
                "repo": {
                    "archived": False,
                    "url": "",
                    "html_url": "",
                    "default_branch": github_types.GitHubRefType(""),
                    "id": github_types.GitHubRepositoryIdType(123),
                    "full_name": "fork/other",
                    "name": github_types.GitHubRepositoryName("other"),
                    "private": False,
                    "owner": {
                        "login": github_types.GitHubLogin("user"),
                        "id": github_types.GitHubAccountIdType(0),
                        "type": "User",
                        "avatar_url": "",
                    },
                },
            },
            "user": {
                "login": github_types.GitHubLogin("user"),
                "id": github_types.GitHubAccountIdType(0),
                "type": "User",
                "avatar_url": "",
            },
            "merged_by": None,
            "merged_at": None,
            "mergeable_state": "clean",
            "mergeable": True,
        },
    )
    assert await ctxt.get_cached_last_summary_head_sha() is None
    await ctxt.set_summary_check(
        check_api.Result(check_api.Conclusion.SUCCESS, "foo", "bar")
    )

    assert await ctxt.get_cached_last_summary_head_sha() == "old-sha-one"
    await ctxt.clear_cached_last_summary_head_sha()

    assert await ctxt.get_cached_last_summary_head_sha() is None
