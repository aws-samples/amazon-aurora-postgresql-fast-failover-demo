# Amazon Aurora PostgreSQL Fast Failover Demo

## A simple demonstration of in-region (HA) and cross-region (DR) failover automation using Amazon RDS Aurora PostgreSQL Global Database, RDS Proxy and Route53

## Cross-Region Recovery
- The CloudFormation template sets up a two-region database cluster for Diaster Recoveryand statically stable application routing to the local databse cluster.
- A Lambda canary process continually stans the primary region (every 10 seconds) from the secondary region, and enacts failover if it observes 30 seconds of consecutive failures.
 
![architecture for cross-region failover](architecture_multi_region.png)

## In-Region Recovery
- Each region also contains an RDS Proxy to provide High Availability transparent failover to the failved-over writer in the secondary Availability Zone.
- By queueing read and write queries until the reader instance comes back as a writer, RDS Proxy turns what would be SQL errors into a few extra seconds of latency for the application.

![architecture for cross-region failover](architecture_multi_region.png)

## Demos
- The repository also contains a test application to produce load for the application and log successful calls and errors in a simple UI, and times the failover
- In-region failover with and without RDS proxy

## Deploying This Solution
- This solution can be deployed using a single **main** CloudFormation template [located here](cloudformation/). Both main.yml and main.json are functionally identical. This template takes roughly 60 minutes to deploy.
- During deployment, this template will launch several additional multi-region CloudFormation StackSets to fully deploy the required resources. While you don't need to launch or modify these StackSets directly, the underlying templates have been included in this repo for your reference.
- Once deployed, the primary stack you launch will contain the following outputs:

  - **InRegionFailoverDemoUrl** - The dashboard you can use to simulate an in-region failover.
  - **CrossRegionFailoverDemoUrl** - The dashboard you can use to simulate a cross-region failover.

- This template implements several mechanisms that may be useful to you outside of this use case. These mechanisms can be extracted from this repo and used elsewhere in your environment. These mechanisms include using CloudFormation to:
  - Empty an Amazon S3 bucket prior to deletion by CloudFormation.
  - Download code from a public repo URL and deploy it to Amazon S3.
  - Retrieve CloudFormation Exports from another AWS Region and use them as variables inside the invoking template.
  - Create a cross-region VPC Peering Connection and configure the required VPC routes on both sides.
  - Create a custom AWS Lambda Layer for Python runtimes. This tooling takes, as input, the PyPI packages you want included in the layer, as well as any custom functions, then returns the resulting Layer Version ARN for use elsewhere in your template(s).
  - Execute DDL statements against a remote database in need of configuration. In the case of this solution, this tooling is used to initialize an RDS Aurora PostgreSQL database. However, using the custom Lambda Layer creation tooling mentioned above, it could be easily modified to target additional DB engines (e.g., MySQL, MariaDB).
  - Delete some or all DNS records within an Amazon Route53 Hosted Zone during a CloudFormation Stack deletion. By default, CloudFormation's AWS::Route53::RecordSet[Group] resource handlers will NOT delete DNS records if they have a value different than that which was used at their creation. If your application modifies DNS records created by CloudFormation, CloudFormation will not delete them in an effort to protect customers from inadvertently deleting records that are still needed. The mechanism included in this solution is indiscriminate when it comes to deletion. It takes, as input, the FQDN(s) you would like deleted from the specified Hosted Zone and deletes those records, regardless of their current values.

## Cleaning Up This Solution
- To clean up / undeploy this solution, simply delete the primary CloudFormation Stack you initially launched. The cleanup will take roughly 45 minutes.

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the LICENSE file.

Note that the Python code depends on, but does not include, the LGPL-3.0 licensed Psycopg PostgreSQL adapter.
