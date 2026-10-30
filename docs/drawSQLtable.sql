CREATE TABLE `roles`(
    `id` INT NOT NULL,
    `name` VARCHAR(30) NOT NULL,
    PRIMARY KEY(`id`)
);
ALTER TABLE
    `roles` ADD UNIQUE `roles_name_unique`(`name`);
CREATE TABLE `users`(
    `id` INT NOT NULL,
    `role_id` INT NOT NULL,
    `full_name` VARCHAR(120) NOT NULL,
    `email` VARCHAR(120) NOT NULL,
    `password_hash` VARCHAR(255) NOT NULL,
    `faculty` VARCHAR(120) NULL,
    `created_at` TIMESTAMP NOT NULL,
    PRIMARY KEY(`id`)
);
ALTER TABLE
    `users` ADD UNIQUE `users_email_unique`(`email`);
CREATE TABLE `buildings`(
    `id` INT NOT NULL,
    `name` VARCHAR(120) NOT NULL,
    `address` VARCHAR(255) NOT NULL,
    `latitude` DECIMAL(9, 6) NULL,
    `longitude` DECIMAL(9, 6) NULL,
    PRIMARY KEY(`id`)
);
CREATE TABLE `room_types`(
    `id` INT NOT NULL,
    `name` VARCHAR(60) NOT NULL,
    PRIMARY KEY(`id`)
);
ALTER TABLE
    `room_types` ADD UNIQUE `room_types_name_unique`(`name`);
CREATE TABLE `rooms`(
    `id` INT NOT NULL,
    `building_id` INT NOT NULL,
    `room_type_id` INT NOT NULL,
    `number` VARCHAR(20) NOT NULL,
    `name` VARCHAR(120) NOT NULL,
    `floor` INT NULL,
    `capacity` INT NOT NULL,
    `description` TEXT NULL,
    `requires_approval` BOOLEAN NOT NULL,
    `is_active` BOOLEAN NOT NULL DEFAULT 1,
    `open_time` TIME NOT NULL,
    `close_time` TIME NOT NULL,
    PRIMARY KEY(`id`)
);
CREATE TABLE `room_photos`(
    `id` INT NOT NULL,
    `room_id` INT NOT NULL,
    `url` VARCHAR(255) NOT NULL,
    `is_main` BOOLEAN NOT NULL,
    `sort_order` INT NOT NULL,
    PRIMARY KEY(`id`)
);
CREATE TABLE `equipment`(
    `id` INT NOT NULL,
    `name` VARCHAR(80) NOT NULL,
    `icon` VARCHAR(50) NULL,
    PRIMARY KEY(`id`)
);
ALTER TABLE
    `equipment` ADD UNIQUE `equipment_name_unique`(`name`);
CREATE TABLE `room_equipment`(
    `room_id` INT NOT NULL,
    `equipment_id` INT NOT NULL,
    `quantity` INT NOT NULL DEFAULT 1,
    PRIMARY KEY(`room_id`)
);
ALTER TABLE
    `room_equipment` ADD PRIMARY KEY(`equipment_id`);
CREATE TABLE `access_rules`(
    `id` INT NOT NULL,
    `room_id` INT NOT NULL,
    `title` VARCHAR(120) NOT NULL,
    `description` TEXT NOT NULL,
    `allowed_role_id` INT NULL,
    PRIMARY KEY(`id`)
);
CREATE TABLE `recurring_rules`(
    `id` INT NOT NULL,
    `user_id` INT NOT NULL,
    `room_id` INT NOT NULL,
    `frequency` VARCHAR(10) NOT NULL,
    `weekdays` VARCHAR(20) NULL,
    `start_time` TIME NOT NULL,
    `end_time` TIME NOT NULL,
    `start_date` DATE NOT NULL,
    `end_date` DATE NOT NULL,
    `is_active` BOOLEAN NOT NULL DEFAULT 1,
    PRIMARY KEY(`id`)
);
CREATE TABLE `bookings`(
    `id` INT NOT NULL,
    `user_id` INT NOT NULL,
    `room_id` INT NOT NULL,
    `recurring_id` INT NULL,
    `starts_at` TIMESTAMP NOT NULL,
    `ends_at` TIMESTAMP NOT NULL,
    `purpose` VARCHAR(255) NULL,
    `attendees` INT NULL,
    `status` VARCHAR(15) NOT NULL,
    `created_at` TIMESTAMP NOT NULL,
    PRIMARY KEY(`id`)
);
CREATE TABLE `approvals`(
    `id` INT NOT NULL,
    `booking_id` INT NOT NULL,
    `admin_id` INT NOT NULL,
    `decision` VARCHAR(10) NOT NULL,
    `comment` TEXT NULL,
    `decided_at` TIMESTAMP NOT NULL,
    PRIMARY KEY(`id`)
);
ALTER TABLE
    `approvals` ADD UNIQUE `approvals_booking_id_unique`(`booking_id`);
CREATE TABLE `reviews`(
    `id` INT NOT NULL,
    `user_id` INT NOT NULL,
    `room_id` INT NOT NULL,
    `booking_id` INT NULL,
    `cleanliness` INT NOT NULL,
    `equipment_score` INT NOT NULL,
    `comfort` INT NOT NULL,
    `comment` TEXT NULL,
    `created_at` TIMESTAMP NOT NULL,
    PRIMARY KEY(`id`)
);
CREATE TABLE `notifications`(
    `id` INT NOT NULL,
    `user_id` INT NOT NULL,
    `booking_id` INT NULL,
    `type` VARCHAR(20) NOT NULL,
    `message` VARCHAR(255) NOT NULL,
    `is_read` BOOLEAN NOT NULL,
    `created_at` TIMESTAMP NOT NULL,
    PRIMARY KEY(`id`)
);
ALTER TABLE
    `rooms` ADD CONSTRAINT `rooms_room_type_id_foreign` FOREIGN KEY(`room_type_id`) REFERENCES `room_types`(`id`);
ALTER TABLE
    `reviews` ADD CONSTRAINT `reviews_booking_id_foreign` FOREIGN KEY(`booking_id`) REFERENCES `bookings`(`id`);
ALTER TABLE
    `room_equipment` ADD CONSTRAINT `room_equipment_equipment_id_foreign` FOREIGN KEY(`equipment_id`) REFERENCES `equipment`(`id`);
ALTER TABLE
    `room_equipment` ADD CONSTRAINT `room_equipment_room_id_foreign` FOREIGN KEY(`room_id`) REFERENCES `rooms`(`id`);
ALTER TABLE
    `access_rules` ADD CONSTRAINT `access_rules_allowed_role_id_foreign` FOREIGN KEY(`allowed_role_id`) REFERENCES `roles`(`id`);
ALTER TABLE
    `reviews` ADD CONSTRAINT `reviews_room_id_foreign` FOREIGN KEY(`room_id`) REFERENCES `rooms`(`id`);
ALTER TABLE
    `bookings` ADD CONSTRAINT `bookings_user_id_foreign` FOREIGN KEY(`user_id`) REFERENCES `users`(`id`);
ALTER TABLE
    `users` ADD CONSTRAINT `users_role_id_foreign` FOREIGN KEY(`role_id`) REFERENCES `roles`(`id`);
ALTER TABLE
    `recurring_rules` ADD CONSTRAINT `recurring_rules_user_id_foreign` FOREIGN KEY(`user_id`) REFERENCES `users`(`id`);
ALTER TABLE
    `bookings` ADD CONSTRAINT `bookings_room_id_foreign` FOREIGN KEY(`room_id`) REFERENCES `rooms`(`id`);
ALTER TABLE
    `rooms` ADD CONSTRAINT `rooms_building_id_foreign` FOREIGN KEY(`building_id`) REFERENCES `buildings`(`id`);
ALTER TABLE
    `recurring_rules` ADD CONSTRAINT `recurring_rules_room_id_foreign` FOREIGN KEY(`room_id`) REFERENCES `rooms`(`id`);
ALTER TABLE
    `room_photos` ADD CONSTRAINT `room_photos_room_id_foreign` FOREIGN KEY(`room_id`) REFERENCES `rooms`(`id`);
ALTER TABLE
    `access_rules` ADD CONSTRAINT `access_rules_room_id_foreign` FOREIGN KEY(`room_id`) REFERENCES `rooms`(`id`);
ALTER TABLE
    `notifications` ADD CONSTRAINT `notifications_booking_id_foreign` FOREIGN KEY(`booking_id`) REFERENCES `bookings`(`id`);
ALTER TABLE
    `approvals` ADD CONSTRAINT `approvals_booking_id_foreign` FOREIGN KEY(`booking_id`) REFERENCES `bookings`(`id`);
ALTER TABLE
    `approvals` ADD CONSTRAINT `approvals_admin_id_foreign` FOREIGN KEY(`admin_id`) REFERENCES `users`(`id`);
ALTER TABLE
    `bookings` ADD CONSTRAINT `bookings_recurring_id_foreign` FOREIGN KEY(`recurring_id`) REFERENCES `recurring_rules`(`id`);
ALTER TABLE
    `reviews` ADD CONSTRAINT `reviews_user_id_foreign` FOREIGN KEY(`user_id`) REFERENCES `users`(`id`);
ALTER TABLE
    `notifications` ADD CONSTRAINT `notifications_user_id_foreign` FOREIGN KEY(`user_id`) REFERENCES `users`(`id`);